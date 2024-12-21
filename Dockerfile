FROM ntr.nwie.net/library/python:3.11-slim-bullseye
ENV TZ="America/New_York"
WORKDIR /usr/src/app

COPY . .

RUN apt update -y \
    && apt -y upgrade \
    && apt install -y unzip \
    && apt install -y curl \
    && apt install -y libglib2.0-0 \
    && apt install -y libx11-6 \
    && apt install -y libnss3 \
    && apt install -y libosmesa6 \
    && apt install -y libosmesa6-dev \
    && apt install -y chromium

RUN pip config set global.index-url https://art.nwie.net/artifactory/api/pypi/pypi/simple \
    && pip install \
    --index-url=http://art.nwie.net/artifactory/api/pypi/pypi/simple \
    --trusted-host art.nwie.net \
    --trusted-host files.pythonhosted.org \
    -r requirements.txt

RUN curl -SL https://github.com/adieuadieu/serverless-chrome/releases/download/v1.0.0-57/stable-headless-chromium-amazonlinux-2.zip > headless.zip \
    && curl -SL https://chromedriver.storage.googleapis.com/86.0.4240.22/chromedriver_linux64.zip > cdriver.zip \
    && unzip headless.zip -d /usr/local/bin/ \
    && unzip cdriver.zip -d /usr/local/bin/ \
    && rm headless.zip \
    && rm cdriver.zip
    
RUN rm -rf /usr/lib/python3/dist-packages/certifi \
    && rm -rf /usr/lib/python3/dist-packages/certifi-2020.6.20.egg-info/

EXPOSE 443

CMD [ "python", "nr_thread_profile.py" ]