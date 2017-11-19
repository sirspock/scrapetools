from setuptools import setup


setup(name='scrapetools',
      version='0.2.5',
      description='Web Scraping utility',
      author='Beta Faccion',
      author_email='betafcc@gmail.com',
      packages=['scrapetools'],
      install_requires=['aiohttp', 'tqdm', 'lxml', 'cssselect']
      )
