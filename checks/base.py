"""Base class for all AWS checks"""
from abc import ABC, abstractmethod
from datetime import datetime

class BaseChecker(ABC):
    def __init__(self, region='ap-southeast-3'):
        self.region = region
        self.timestamp = datetime.now()
        
    @abstractmethod
    def check(self, profile, account_id):
        """Execute the check and return results"""
        pass
    
    @abstractmethod
    def format_report(self, results):
        """Format results into readable report"""
        pass
