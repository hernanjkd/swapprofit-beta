import os
import requests

r = requests.get( os.environ['POKERSOCIETY_HOST'] + '/swapprofit/update' )