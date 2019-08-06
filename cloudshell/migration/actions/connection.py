from cloudshell.migration.actions.core import Action


class UpdateConnectionAction(Action):
    priority = Action.EXECUTION_PRIORITY.HIGH

    def __init__(self, src_port, dst_port, connection_operations, updated_connections, logger):
        """
        :type src_port: cloudshell.migration.entities.Port
        :type dst_port: cloudshell.migration.entities.Port
        :type resource_operations: cloudshell.migration.operations.resource_operations.ResourceOperations
        :type updated_connections: dict
        :type logger: cloudshell.migration.helpers.log_helper.Logger
        """
        super(UpdateConnectionAction, self).__init__(logger)
        self.src_port = src_port
        self.dst_port = dst_port
        self.resource_operations = resource_operations
        self.updated_connections = updated_connections

    def execute(self):
        try:
            self.logger.debug('**** Execute action update connection:')
            self.logger.debug('**** {} -> {}'.format(self.src_port.name, self.dst_port.name))
            self.dst_port.connected_to = self.updated_connections.get(self.src_port.connected_to,
                                                                      self.src_port.connected_to)
            self.resource_operations.update_connection(self.dst_port)
            self.updated_connections[self.src_port.name] = self.dst_port.name
            return self.to_string() + " ... Done"
        except Exception as e:
            self.logger.error('Cannot update port {}, reason {}'.format(self.dst_port, str(e)))
            return self.to_string() + "... Failed"

    def to_string(self):
        return 'Update Connection: {}=>{}'.format(self.dst_port.name, self.src_port.connected_to)

    @property
    def _comparable_unit(self):
        return ''.join([self.src_port.name, self.src_port.connected_to or ''])

    def __hash__(self):
        return hash(self._comparable_unit)

    def __eq__(self, other):
        """
        :type other: UpdateConnectionAction
        """
        return self._comparable_unit == other._comparable_unit