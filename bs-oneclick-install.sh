#!/bin/bash
# installs the scripts and what not
set -x
mkdir -p ~/.local/share/applications
mv bs-oneclick.desktop ~/.local/share/applications
xdg-mime default ~/.local/share/applications/bs-oneclick.desktop x-schema-handler/beatsaver x-schema-handler/modelsaber

bs_install="$HOME/.local/share/Steam/steamapps/common/Beat Saber"

zenity --info --title="OneClick Installer" --text="Please navigate to your Beat Saber install directory to properly set up the OneClick Installer." --width=500

while : ; do
	bs_install=$( zenity --file-selection --directory --title="Please navigate to your Beat Saber install directory." )
	if [[ -f "$bs_install/Beat Saber.exe" ]]; then 
		# welcome to slash hell
		bs_install_sed=$( echo $bs_install | sed 's,/,\\/,g' )
		sed -i "s,bs_install=.*,bs_install=\"$bs_install_sed\"," bs-oneclick.sh
		mv bs-oneclick.sh "$bs_install"
		zenity --info --title="OneClick Installer" --text="OneClick Installer installed. Enjoy!" --icon-name="checkbox-checked"
		break
	fi
	
	zenity --error --title="OneClick Installer" --text="Beat Saber installation not detected in that folder. Try again." --width=500
done
