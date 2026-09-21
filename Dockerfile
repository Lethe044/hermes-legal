# Hermes Legal Advisor - runs the web dashboard out of the box.
#
# Build:  docker build -t hermes-legal .
# Run:    docker run -p 8765:8765 -e GROQ_API_KEY=your_key hermes-legal
#
# No API key needed at all if you just want the free offline scanner -
# leave the environment variables out and it still works.

FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src/ ./src/
COPY sample_contracts/ ./sample_contracts/

RUN pip install --no-cache-dir ".[all]"

EXPOSE 8765

ENV HERMES_LEGAL_HOME=/data
VOLUME ["/data"]

ENTRYPOINT ["hermes-legal"]
CMD ["serve", "--host", "0.0.0.0", "--no-browser"]
