class MultiDBRouter:
    def db_for_read(self, model, **hints):
        if model.__name__ == 'DB2Model':
            return 'db2'
        elif model.__name__ == 'DB3Model':
            return 'db3'
        return 'default'

    def db_for_write(self, model, **hints):
        return self.db_for_read(model, **hints)

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if model_name == 'db2model':
            return db == 'db2'
        elif model_name == 'db3model':
            return db == 'db3'
        return db == 'default'
