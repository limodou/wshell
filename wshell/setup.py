import uliweb
from uliweb.utils.setup import setup
import apps

__doc__ = """doc"""

setup(name='wshell',
    version=apps.__version__,
    description="Description of your project",
    package_dir = {'wshell':'apps'},
    packages = ['wshell'],
    include_package_data=True,
    zip_safe=False,
)
