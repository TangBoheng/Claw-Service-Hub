"""
Claw Service Hub Client - pip 安装配置

安装:
    pip install claw-service-hub-client

开发安装:
    cd client
    pip install -e .
"""

from setuptools import setup, find_packages

setup(
    name="claw-service-hub-client",
    version="1.0.0",
    description="Unified client for Claw Service Hub - service discovery, invocation, chat, and trading",
    author="Claw Service Hub Team",
    author_email="",
    url="https://github.com/tangbohao/Claw-Service-Hub",
    license="MIT",
    packages=find_packages(),
    install_requires=[
        "websockets>=10.0",
    ],
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    keywords="claw service hub client websocket rpc",
)