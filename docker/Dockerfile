FROM python:3.8

# Install docker
RUN apt-get update && \
    apt-get install -y ca-certificates curl gnupg lsb-release && \
    mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null && \
    apt update && apt install  docker-ce-cli -y && \
    apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* && rm -rf ~/.cache/

COPY docker/requirements.txt requirements.txt

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY docker/requirements-oscarp.txt requirements-oscarp.txt
RUN pip install --no-cache-dir -r requirements-oscarp.txt

COPY docker/requirements-space4ai.txt requirements-space4ai.txt
RUN pip install --no-cache-dir -r requirements-space4ai.txt

# NOTE: once the repo will be public it will be installed directly from gitlab
# RUN pip install git+https://gitlab.polimi.it/ai-sprint/ai-sprint-design.git

COPY . /ai-sprint-design

RUN git clone https://gitlab.polimi.it/ai-sprint/OSCAR-P.git /ai-sprint-design/src/aisprint/oscarpcoordinator && \
    cp -r /ai-sprint-design/src/aisprint/oscarpcoordinator/oscarp/executables /bin/oscarp_executables && \
    cp -r /ai-sprint-design/src/aisprint/oscarpcoordinator/jmeterLoadInjector /jmeterLoadInjector

RUN git clone --recurse-submodules https://gitlab.polimi.it/ai-sprint/space4ai-d.git /ai-sprint-design/src/aisprint/space4aid
ENV PYTHONPATH="${PYTHONPATH}:/usr/local/lib/python3.8/site-packages/aisprint/space4aid/space4ai_parser"
ENV PYTHONPATH="${PYTHONPATH}:/usr/local/lib/python3.8/site-packages/aisprint/space4aid"

RUN cd /ai-sprint-design && python3 -m pip install .
RUN rm -r /ai-sprint-design

RUN git clone https://gitlab.polimi.it/ai-sprint/toscarizer.git && \
    cd toscarizer && \
    pip install . && \
    cd ..  && \
    rm -rf toscarizer

RUN mkdir /.cookiecutter_replay/
RUN chmod 777 -R /.cookiecutter_replay

