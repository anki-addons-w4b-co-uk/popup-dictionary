clear
echo updating -- popup dictionary ankiaddon
7z u popup_dictionary.ankiaddon ../src/* -xr0!__pycache__ -xr!__pycache__
echo done
start popup_dictionary.ankiaddon
exec $SHELL
