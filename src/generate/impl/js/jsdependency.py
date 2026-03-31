import common.label as labelm
import generate


class JsDependency(generate.AbstractDependency):

    @classmethod
    def init_with_artifact_def(clazz, artifact_def):
        label = None
        return JsDependency(label, artifact_def)

    @classmethod
    def init_with_name_and_version(clazz, name, version, repository_name):
        assert name is not None
        assert version is not None
        assert repository_name is not None
        artifact_def = None
        label_name = name.replace("-", "_") # todo move into label?
        label = labelm.Label("@%s//%s" % (repository_name, label_name))
        return JsDependency(label, artifact_def, name, version)
    
    # private
    def __init__(self, label, artifact_def, name=None, version=None):
        super().__init__(label, artifact_def, name, version)

    @property
    def native_repr(self):
        return '"%s": "^%s"' % (self.artifact_id, self.version)
