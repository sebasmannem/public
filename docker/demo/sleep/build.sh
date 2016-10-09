echo 'FROM scratch
ADD sleep /sleep
CMD ["/sleep"]' > ./Dockerfile

cp /usr/bin/sleep .
docker build --rm -t demo/sleep .
docker run -t -i demo/sleep /sleep 10
#docker: Error response from daemon: Container command '/sleep' not found or does not exist..

ldd sleep
#man vdso

mkdir ./lib64
cp /lib64/libc.so.6 ./lib64
cp /lib64/ld-linux-x86-64.so.2 ./lib64
echo 'ADD lib64 /lib64' >> ./Dockerfile
docker build --rm -t demo/sleep .
docker run -t -i demo/sleep
docker run -t -i demo/sleep /sleep 5

