from fastapi import HTTPException
from typing import List

class QualificationService:
    # 需要签字的报告类型
    SIGNATURE_REQUIRED_TYPES = ["房地产估价报告", "资产评估报告", "土地报告"]
    
    # 报告类型与所需资质的映射
    REPORT_QUALIFICATION_MAP = {
        "资产评估报告": "资产评估师",
        "房地产估价报告": "房地产估价师", 
        "土地报告": "土地估价师"
    }
    
    def __init__(self):
        pass
    
    def get_user_qualifications(self, username: str, db) -> List[str]:
        """获取用户的所有资质"""
        c = db.cursor()
        c.execute("SELECT qualification_type FROM user_qualifications WHERE username = ?", (username,))
        qualifications = [row[0] for row in c.fetchall()]
        return qualifications
    
    def validate_report_signature_permission(self, report_type: str, signer_username: str, db) -> bool:
        """验证用户是否有给特定报告类型签字的权限"""
        # 不需要签字的报告类型，任何人都可以签字
        if report_type not in self.SIGNATURE_REQUIRED_TYPES:
            return True
            
        # 需要签字的报告类型，检查用户资质
        required_qualification = self.REPORT_QUALIFICATION_MAP.get(report_type)
        if not required_qualification:
            return False
            
        user_qualifications = self.get_user_qualifications(signer_username, db)
        return required_qualification in user_qualifications
    
    def validate_all_signatures(self, report_type: str, signer1: str, signer2: str, db) -> bool:
        """验证所有签字人的资质"""
        # 不需要签字的报告类型
        if report_type not in self.SIGNATURE_REQUIRED_TYPES:
            return True
            
        # 需要签字的报告类型，验证两个签字人
        if not signer1 or not signer2:
            return False
            
        return (self.validate_report_signature_permission(report_type, signer1, db) and 
                self.validate_report_signature_permission(report_type, signer2, db))

qualification_service = QualificationService()