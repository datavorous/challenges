# Challenges

## Custom Data Compressor

Inspired by [Reddit :: How I was able to fit 1.2GB of cricket data into 50MB](https://www.reddit.com/r/developersIndia/comments/1hu0w88/how_i_was_able_to_fit_12gb_of_cricket_data_into/)

Original Folder Size: 2,872,200,021 bytes (~2.87 GB)  
Custom: 42,462,177 bytes (~42.46 MB)    
gzip: 52,980,912 bytes (~52.98 MB) (`tar -cf - all_json | gzip -9`)  
7z: 45,026,348 bytes (~45.02 MB) (`7z a -t7z -mx=9 -ms=on`)  

Read the [writeup](compressor/README.md).

The goal is to compress a cricket match dataset (Cricsheet JSON format) into the smallest possible representation. 

Standard compression technique finds patterns in text, but mine exploits the predictable schema of the files.

Deals with [Algorithmic Information Theory](https://en.wikipedia.org/wiki/Algorithmic_information_theory).