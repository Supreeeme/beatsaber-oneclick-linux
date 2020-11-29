#!/bin/bash
# installs the scripts and what not
#set -x
set -e

bs_install="$HOME/.local/share/Steam/steamapps/common/Beat Saber"

zenity --info --title="OneClick Installer" --text="Please navigate to your Beat Saber install directory to properly set up the OneClick Installer."

while : ; do
	bs_install=$( zenity --file-selection --directory --title="Please navigate to your Beat Saber install directory." --filename="$HOME/.local/share/Steam/steamapps/common/Beat Saber")
	if [[ -f "$bs_install/Beat Saber.exe" ]]; then 
		cp bs-oneclick-temp bs-oneclick.sh
		cp playlist-installer-temp playlist-installer
		cp bs-oneclick-desktop-temp bs-oneclick.desktop

		mkdir -p ~/.local/share/applications
		xdg-mime default bs-oneclick.desktop x-scheme-handler/beatsaver x-scheme-handler/modelsaber x-scheme-handler/bsplaylist
		# welcome to slash hell
		bs_install_sed=$( echo $bs_install | sed 's,/,\\/,g' )
		sed -i "s,bs_install=.*,bs_install=\"$bs_install_sed\"," bs-oneclick.sh
		sed -i "s,Exec=.*,Exec=\"$bs_install_sed/bs-oneclick.sh\" %u," bs-oneclick.desktop
		mv bs-oneclick.sh "$bs_install"
		mv playlist-installer "$bs_install"
		mv bs-oneclick.desktop ~/.local/share/applications
		zenity --info --title="OneClick Installer" --text="OneClick Installer installed. Enjoy!" --icon-name="checkbox-checked"
		break
	fi
	
	zenity --error --title="OneClick Installer" --text="Beat Saber installation not detected in that folder. Try again."
done
