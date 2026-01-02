#!/usr/bin/env python3
"""
Setup script for Mac Activity Tracker.
"""

from setuptools import setup, find_packages

setup(
    name='mac-activity-tracker',
    version='1.0.0',
    description='Local activity tracking for macOS - monitor apps, websites, and typing',
    author='Your Name',
    python_requires='>=3.9',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'pyobjc-core>=9.0',
        'pyobjc-framework-Cocoa>=9.0',
        'pyobjc-framework-Quartz>=9.0',
        'pyobjc-framework-ApplicationServices>=9.0',
        'pyobjc-framework-ScriptingBridge>=9.0',
        'flask>=3.0.0',
        'flask-cors>=4.0.0',
        'pandas>=2.0.0',
        'numpy>=1.24.0',
        'sqlalchemy>=2.0.0',
        'python-dateutil>=2.8.0',
        'psutil>=5.9.0',
        'rumps>=0.4.0',
    ],
    entry_points={
        'console_scripts': [
            'activity-tracker=main:main',
        ],
    },
    package_data={
        'src.web': ['templates/*.html', 'static/css/*.css', 'static/js/*.js'],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: MacOS X',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: MIT License',
        'Operating System :: MacOS :: MacOS X',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Topic :: System :: Monitoring',
    ],
)
