class Plugin(object):
    def __init__(self, conf):
        self.conf = conf
        self.name = conf['name']
        self.update()

    def update(self):
        raise(NotImplementedError('plugin module is missing update() method'))
