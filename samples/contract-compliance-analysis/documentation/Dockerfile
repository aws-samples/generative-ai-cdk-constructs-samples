FROM ruby:3.4

# Set working directory
WORKDIR /app

# Install system dependencies for PDF generation
RUN apt-get update && apt-get install -y \
    fontconfig \
    fonts-dejavu-core \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Install AsciiDoc gems
RUN gem install asciidoctor \
                asciidoctor-pdf \
                asciidoctor-lists \
                rouge

# Copy your documentation files
COPY . .

# Default command matches your usage pattern
CMD ["bash", "-c", "asciidoctor-pdf --theme=custom-theme.yml -r asciidoctor-lists -a currentdate=\"$(date '+%B %-d, %Y')\" report.adoc"]