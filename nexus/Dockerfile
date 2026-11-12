FROM python:3.11-slim

# System dependencies + mecab base
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    automake \
    autoconf \
    libtool \
    && rm -rf /var/lib/apt/lists/*

# 1) mecab-ko 엔진 먼저 설치
RUN curl -fsSL https://bitbucket.org/eunjeon/mecab-ko/downloads/mecab-0.996-ko-0.9.2.tar.gz \
    | tar xz -C /tmp \
    && cd /tmp/mecab-0.996-ko-0.9.2 \
    && ./configure \
    && make \
    && make install \
    && ldconfig \
    && rm -rf /tmp/mecab-0.996-ko-0.9.2

# 2) mecab-ko-dic 한국어 사전 설치
RUN curl -fsSL https://bitbucket.org/eunjeon/mecab-ko-dic/downloads/mecab-ko-dic-2.1.1-20180720.tar.gz \
    | tar xz -C /tmp \
    && cd /tmp/mecab-ko-dic-2.1.1-20180720 \
    && (autoreconf -fi || ./autogen.sh) \
    && ./configure \
    && make \
    && make install \
    && rm -rf /tmp/mecab-ko-dic-2.1.1-20180720

WORKDIR /app

# Python dependencies — **before** the code, so a code change does not reinstall them.
# Only pyproject.toml and constraints.txt decide this layer; the dependency list is read
# straight from pyproject.toml so it cannot drift from what the package declares.
# notion + a2a extras are baked in so the CLI composition root works out of the box:
# `nexus ingest-notion` wires the a2a-resident default external-ingest sink, and the
# importer reads from Notion via notion-client. (a2a *routes* remain flag-gated off by
# default — NEXUS_A2A_ENABLED — installing the SDK changes no runtime behavior.)
# slack is baked in too so the same image can run the `--profile slack` bot service;
# the profile (not the image) decides whether the bot actually runs.
#
# -c constraints.txt pins the resolved set. The image is the `nexus (search recall, mecab)`
# CI job's environment as well as the deployed one, so leaving it to re-resolve is the same
# exposure as an unpinned CI install — the build just happens to be a Dockerfile.
COPY pyproject.toml constraints.txt ./
RUN python -c "import tomllib; p = tomllib.load(open('pyproject.toml', 'rb'))['project']; extras = ('dev', 'notion', 'a2a', 'slack'); print(chr(10).join(p['dependencies'] + [d for e in extras for d in p['optional-dependencies'][e]]))" > /tmp/requirements.txt \
    && pip install --no-cache-dir -r /tmp/requirements.txt -c constraints.txt \
    && rm /tmp/requirements.txt

# Application code, then the package itself (no dependency resolution — done above).
COPY . .
RUN pip install --no-cache-dir --no-deps -e .

# mecab 동작 확인 — 사전과 파이썬 바인딩이 실제로 도는가. 실패하면 **빌드가 실패한다**:
# 예전에는 `|| echo skipped` 라 사전이 없는 이미지도 초록으로 나왔고, 그러면 한국어 BM25 가
# 조용히 형태소 분석 없이 돈다.
RUN echo "결제 서비스가 알림을 보낸다" | mecab \
    && python -c "import MeCab; MeCab.Tagger().parse('결제 서비스')"

EXPOSE 8000

CMD ["uvicorn", "nexus.api:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
