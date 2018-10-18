import click

from cloudshell.layer_one.migration_tool.operational_entities.config_unit import ConfigUnit
from cloudshell.layer_one.migration_tool.operational_entities.migration_config import MigrationConfig
from cloudshell.layer_one.migration_tool.operational_entities.migration_operation import MigrationOperation
from cloudshell.layer_one.migration_tool.operational_entities.resource import Resource
from cloudshell.layer_one.migration_tool.validators.config_unit_validator import ConfigUnitValidator


class MigrationConfigHandler(object):
    SEPARATOR = ','
    ADDRESS_KEY = 'address'
    FAMILY_KEY = 'family'
    MODEL_KEY = 'model'
    NEW_RESOURCE_NAME_PREFIX = 'new_'

    def __init__(self, api, logger, name_prefix):
        """
        :type api: cloudshell.api.cloudshell_api.CloudShellAPISession
        """
        name_prefix = name_prefix or self.NEW_RESOURCE_NAME_PREFIX
        self._name_template = name_prefix + '{}'
        self._api = api
        self._logger = logger
        self._config_unit_validator = ConfigUnitValidator(logger)
        self.__installed_resources = {}

    def parse_migration_configuration(self, old_resources_str, new_resources_str):
        """
        :type old_resources_str: str
        :type new_resources_str: str
        """
        migration_config_list = []
        old_resources_conf_list = old_resources_str.split(self.SEPARATOR)
        new_resources_conf_list = new_resources_str.split(self.SEPARATOR)

        for index in xrange(len(old_resources_conf_list)):
            if len(new_resources_conf_list) == 1:
                migration_config_list.append(
                    MigrationConfig(ConfigUnit(old_resources_conf_list[index]), ConfigUnit(new_resources_conf_list[0])))
            else:
                migration_config_list.append(
                    MigrationConfig(ConfigUnit(old_resources_conf_list[index]),
                                    ConfigUnit(new_resources_conf_list[index])))

        return migration_config_list

    @property
    def _installed_resources(self):
        if not self.__installed_resources:
            for resource in self._api.GetResourceList().Resources:
                name = resource.Name
                address = resource.Address
                resource_family = resource.ResourceFamilyName
                resource_model = resource.ResourceModelName
                self.__installed_resources[name] = {self.FAMILY_KEY: resource_family, self.MODEL_KEY: resource_model,
                                                    self.ADDRESS_KEY: address}
        return self.__installed_resources

    def define_migration_operations(self, migration_config):
        """
        :type migration_config: cloudshell.layer_one.migration_tool.entities.migration_config.MigrationConfig
        """
        if not migration_config.valid:
            return []

        if migration_config.old_config.is_multi_resource():
            operations = self._define_multiple_operations(migration_config)
        else:
            operations = self._define_single_operation(migration_config)
        return operations

    def _define_multiple_operations(self, migration_config):
        """
        :type migration_config: cloudshell.layer_one.migration_tool.entities.migration_config.MigrationConfig
        """
        self._config_unit_validator.validate_family(migration_config.old_config)
        self._config_unit_validator.validate_model(migration_config.old_config)
        self._config_unit_validator.validate_family(migration_config.new_config)
        self._config_unit_validator.validate_model(migration_config.new_config)

        operations = []
        for old_resource_name in self._get_resources_by_family_model(migration_config.old_config.resource_family,
                                                                     migration_config.old_config.resource_model):
            old_resource = self._create_resource(migration_config.old_config, old_resource_name)
            new_resource = self._create_resource(migration_config.new_config, self._generate_name(old_resource_name))
            operations.append(
                MigrationOperation(old_resource, new_resource,
                                   migration_config))
        return operations

    def _define_single_operation(self, migration_config):
        """
        :type migration_config: cloudshell.layer_one.migration_tool.entities.migration_config.MigrationConfig
        """
        old_resource = self._create_resource(migration_config.old_config)
        new_resource_name = migration_config.new_config.resource_name or self._generate_name(old_resource.name)
        new_resource = self._create_resource(migration_config.new_config, new_resource_name)
        return [MigrationOperation(old_resource, new_resource, migration_config)]

    def _generate_name(self, name):
        return self._name_template.format(name)

    def _get_resources_by_family_model(self, family, model):
        resources_list = []
        for name, details in self._installed_resources.iteritems():
            resource_family = details.get(self.FAMILY_KEY)
            resource_model = details.get(self.MODEL_KEY)
            if family == resource_family and model == resource_model:
                resources_list.append(name)
        return resources_list

    def _create_resource(self, config_unit, name=None):
        """
        :type config_unit: cloudshell.layer_one.migration_tool.entities.config_unit.ConfigUnit
        """
        if not name:
            name = config_unit.resource_name

        if not name:
            raise Exception(self.__class__.__name__, 'Resource name is not defined')

        if name in self._installed_resources:
            resource_family = self._installed_resources.get(name).get(self.FAMILY_KEY)
            resource_model = self._installed_resources.get(name).get(self.MODEL_KEY)
            address = self._installed_resources.get(name).get(self.ADDRESS_KEY)
            if config_unit.resource_family and config_unit.resource_family != resource_family or \
                    config_unit.resource_model and config_unit.resource_model != resource_model:
                raise click.ClickException(
                    'Resource Family or Model for name {} does not coincide with existent'.format(name))
            return Resource(name, address=address, family=resource_family, model=resource_model, exist=True)
        else:
            return Resource(name, family=config_unit.resource_family, model=config_unit.resource_model,
                            driver=config_unit.resource_driver)