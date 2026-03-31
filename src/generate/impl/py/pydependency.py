import common.label as labelm
import generate


class PyDependency(generate.AbstractDependency):

    @classmethod
    def init_with_artifact_def(clazz, artifact_def):
        label = None
        return PyDependency(label, artifact_def)

    @classmethod
    def init_with_name_and_version(clazz, name, version, extras, repository_name):
        assert name is not None
        assert version is not None
        assert repository_name is not None
        assert extras is None or isinstance(extras, (list, tuple))
        artifact_def = None
        label_name = name.replace("-", "_") # todo - move into label
        label = labelm.Label("@%s//%s" % (repository_name, label_name))
        return PyDependency(label, artifact_def, name, version, extras)
    
    # private
    def __init__(self, label, artifact_def, name=None, version=None, extras=None):
        super().__init__(label, artifact_def, name, version)
        self._extras = tuple(extras) if extras is not None else ()

    @property
    def extras(self):
        return self._extras

    @property
    def native_repr(self):
        extras_str = ""
        if len(self.extras) > 0:
            extras_str = "[%s]" % ",".join(self.extras)
        return f"{self.artifact_id}{extras_str}>={self.version}"
