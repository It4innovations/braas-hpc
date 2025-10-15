#!/bin/bash

###############################################
rank=$PMI_RANK

FRAME=$1
frame_start=$2
frame_end=$3
frame_step=$4

blender_version=$5
IN_DIR=$6
BLEND_FILE=$7
OUT_DIR=$8
LOG=$9
ERR=$10

frame_current=$(( ${FRAME} + ${rank} * ${frame_step} ))
###############################################
#ml Blender/${blender_version}
#ml apptainer
ml CUDA
ml Mesa
###############################################
#apptainer exec -B /scratch -B /mnt -B /apps -B ${CUDA_ROOT}:/usr/local/cuda --nv /apps/all/OS/Ubuntu/ubuntu_blender/ubuntu_blender.img /apps/all/Blender/${blender_version}/
if [ ${frame_end} -ge ${frame_current} ]; then
  DISPLAY=:0.${rank} ~/blender/blender --factory-startup --enable-autoexec -noaudio --background ${IN_DIR}/${BLEND_FILE} -E BLENDER_WORKBENCH --render-output ${OUT_DIR}/###### --render-frame ${frame_current} >> ${LOG}.${rank} 2>> ${ERR}.${rank}
fi
###############################################