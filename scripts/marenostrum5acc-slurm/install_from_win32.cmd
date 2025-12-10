@echo off
REM ######################################################################
REM # This program is free software; you can redistribute it and/or modify
REM # it under the terms of the GNU General Public License as published by
REM # the Free Software Foundation; either version 3 of the License, or
REM # (at your option) any later version.
REM #
REM # This program is distributed in the hope that it will be useful, but
REM # WITHOUT ANY WARRANTY; without even the implied warranty of
REM # MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
REM # General Public License for more details.
REM #
REM # You should have received a copy of the GNU General Public License
REM # along with this program. If not, see <http://www.gnu.org/licenses/>.

REM # (c) IT4Innovations, VSB-TUO
REM ######################################################################

REM Download Blender 4.5.5 for Linux
echo Downloading Blender 4.5.5 for Linux...
REM powershell -Command "Invoke-WebRequest -Uri 'https://ftp.nluug.nl/pub/graphics/blender/release/Blender4.5/blender-4.5.5-linux-x64.tar.xz' -OutFile 'blender-4.5.5-linux-x64.tar.xz'"

REM Transfer Blender archive to MareNostrum5 cluster
echo Transferring Blender archive to MareNostrum5...
scp blender-4.5.5-linux-x64.tar.xz MareNostrum5:~/blender.tar.xz

REM Run the Linux installation script
echo Running installation script on MareNostrum5...
ssh MareNostrum5 "if [ -d ~/blender ] ; then rm -rf ~/blender ; fi ; cd ~/ ; tar -xf blender.tar.xz ; mv blender-4.5.5-linux-x64 ~/blender ; rm blender.tar.xz ;"

REM ######################################################################

REM Download braas-hpc for Linux
echo Downloading braas-hpc for Linux...
powershell -Command "Invoke-WebRequest -Uri 'https://github.com/It4innovations/braas-hpc/archive/refs/heads/main.zip' -OutFile 'braas-hpc-main.zip'"

REM Transfer braas-hpc archive to MareNostrum5 cluster
echo Transferring braas-hpc archive to MareNostrum5...
scp braas-hpc-main.zip MareNostrum5:~/braas-hpc.zip

REM Run the Linux installation script
echo Running installation script on MareNostrum5...
ssh MareNostrum5 "if [ -d ~/braas-hpc ] ; then rm -rf ~/braas-hpc ; fi ; cd ~/ ; unzip braas-hpc.zip ; mv braas-hpc-main ~/braas-hpc ; rm braas-hpc.zip ;"

REM ######################################################################
echo Installation completed.

pause
