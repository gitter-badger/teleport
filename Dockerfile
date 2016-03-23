FROM ubuntu:vivid

# Set the locale
RUN locale-gen en_US.UTF-8
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8

RUN apt-get update
RUN apt-get install -y build-essential git wget curl unzip

# Install Python
RUN apt-get install -y python3 python3-pip python3-lxml

# Install Haxe
ENV HAXEURL http://haxe.org/website-content/downloads/3.2.1/downloads/haxe-3.2.1-linux64.tar.gz
ENV HAXEPATH /root/haxe
ENV HAXE_STD_PATH $HAXEPATH/std/
ENV PATH $HAXEPATH:$PATH

RUN mkdir $HAXEPATH
RUN wget -O - $HAXEURL | tar xzf - --strip=1 -C $HAXEPATH

# Install Node JS
RUN curl -sL https://deb.nodesource.com/setup_5.x | bash -
RUN apt-get install -y nodejs

# Install build utilities
RUN pip3 install sphinx==1.3.6
RUN pip3 install xml2rfc==2.5.1

RUN mkdir /build
ADD package.json /build/
WORKDIR /build
RUN npm install

ADD . /build/

RUN mkdir .cache