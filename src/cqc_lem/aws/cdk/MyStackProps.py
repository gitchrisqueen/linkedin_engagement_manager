from aws_cdk import StackProps


class MyStackProps (StackProps):
    def __init__(self,
                 **kwargs):
        super().__init__()
        self.props = kwargs

    def get(self, key):
        return self.props.get(key)

    @property
    def outputs(self):
        return self.get('outputs')