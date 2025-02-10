#!/bin/csh

# Check that at least 1 run number is provided
if ($#argv == 0) then
	echo "Usage: $0 <run numbers>"
	exit 1
endif
# Loop through run list
foreach file ($argv)
	jcache get /mss/hallc/c-nps/raw/nps_coin_${file}.dat.* -D14
	echo "Processing: /mss/hallc/c-nps/raw/nps_coin_${file}.dat.*"
end


# bash option
#for file in {1250,1251,1252,1253,1259,1534,1535,1536}; do
#	jcache get /mss/hallc/c-nps/raw/nps_coin_$file.dat.* -D14
#	echo "Processing: /mss/hallc/c-nps/raw/nps_coin_$file.dat.*"
#done

