#!/bin/bash

echo "🔧 Installing system dependencies including distutils..."

apt-get update
apt-get install -y wget unzip python3-distutils

# Install Chromium
curl -sSL https://storage.googleapis.com/chrome-for-testing-public/122.0.6261.111/linux64/chrome-linux64.zip -o chrome.zip
unzip chrome.zip -d /opt/
mv /opt/chrome-linux64 /opt/chrome
rm chrome.zip

# Install Chromedriver
curl -sSL https://storage.googleapis.com/chrome-for-testing-public/122.0.6261.111/linux64/chromedriver-linux64.zip -o chromedriver.zip
unzip chromedriver.zip -d /opt/chrome/
chmod +x /opt/chrome/chromedriver-linux64/chromedriver
mv /opt/chrome/chromedriver-linux64/chromedriver /opt/chrome/
rm -rf chromedriver.zip /opt/chrome/chromedriver-linux64

echo "✅ Chrome, Chromedriver, and distutils installed."
