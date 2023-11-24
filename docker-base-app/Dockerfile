FROM python:3.8
LABEL maintainer="Miguel Caballer <micafer1@upv.es>"
LABEL version="0.1"
LABEL description="Base container image for the AI-SPRINT use cases."

ARG GIT_USER=user
ARG GIT_PASSWORD=pass

RUN apt update && \
    apt install -y --no-install-recommends uuid-runtime && \
    apt-get autoremove -y && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* && rm -rf ~/.cache/

RUN pip install --upgrade pip
RUN pip install --no-cache-dir \
    numpy==1.23.0
RUN pip install --no-cache-dir pandas    
RUN pip install --no-cache-dir PyYAML
RUN pip install --no-cache-dir \
    boto3

# Install AI-Sprint Lib:
RUN git clone https://$GIT_USER:$GIT_PASSWORD@gitlab.polimi.it/ai-sprint/ai-sprint-design.git && \
    cd ai-sprint-design && \
    pip install . && \
    cd ..  && \
    rm -rf ai-sprint-design

# Install AI-Sprint monitoring Lib:
RUN git clone https://$GIT_USER:$GIT_PASSWORD@gitlab.polimi.it/ai-sprint/pymonitoring.git && \
    cd pymonitoring && \
    pip install . && \
    cd .. && \
    rm -rf pymonitoring
