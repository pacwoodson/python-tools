#!/bin/sh 
dirname=$1
find "$dirname" -type f | sed 's_.*/__' | sort|  uniq -d| 
while read fileName
do
find $dirname -type f | grep "$fileName"
done
