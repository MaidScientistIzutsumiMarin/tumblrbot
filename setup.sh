sleep 3
echo "We are going to install the necessary packages for the project"
echo "It is assumed that you already have python3.11, pip3 and virtualenv installed"
echo "If you don't have them installed, please install them before running this script"
echo "Do you want to continue? (y/n)"
read answer
if [ "$answer" != "${answer#[Yy]}" ] ;then
    python3 -m venv .venv
    source .venv/bin/activate
    pip3 install -r requirements.txt
    echo "Installation completed"
else
    echo "Installation aborted"
fi