from fastapi import HTTPException
from fastapi.responses import RedirectResponse
from datetime import datetime
import os
from utils.helpers import secure_filename

class ReportService:
    def __check_report_permission(self, user, project_creator, project_leader, report_creator):
        return (user.get("user_type") == "admin" or user.get("username") == report_creator)

    async def update_report(self, project_id, report_no, reviewer1, reviewer2, reviewer3,
                      signer1, signer2, report_files, user, db):
        try:
            c = db.cursor()
            c.execute("SELECT status FROM projects WHERE id = ?", (project_id,))
            result = c.fetchone()
            
            if not result:
                raise HTTPException(status_code=404, detail="项目不存在")
            
            status = result[0]
            if status in ['completed', 'paused', 'cancelled']:
                raise HTTPException(status_code=400, detail=f"项目状态为{status}，无法更新报告")
            
            # 获取报告信息，包括创建人
            c.execute("SELECT id, file_paths, reviewer1, reviewer2, reviewer3, signer1, signer2, creator FROM reports WHERE report_no = ? AND project_id = ?", (report_no, project_id))
            result = c.fetchone()
            
            if not result:
                raise HTTPException(status_code=404, detail="报告不存在")
            
            report_id = result[0]
            existing_files = result[1] if result[1] else ""
            existing_reviewer1 = result[2]
            existing_reviewer2 = result[3]
            existing_reviewer3 = result[4]
            existing_signer1 = result[5]
            existing_signer2 = result[6]
            report_creator = result[7]
            
            # 权限验证：只有管理员、项目创建人、项目负责人或报告创建人可以编辑
            c.execute("SELECT creator, project_leader FROM projects WHERE id = ?", (project_id,))
            project_result = c.fetchone()
            if not project_result:
                raise HTTPException(status_code=404, detail="项目不存在")
            
            project_creator = project_result[0]
            project_leader = project_result[1]
            
            if not self.__check_report_permission(user, project_creator, project_leader, report_creator):
                raise HTTPException(status_code=403, detail="没有权限编辑此报告")
        
            file_paths = []
            for report_file in report_files:
                if report_file.filename:
                    report_filename = secure_filename(report_file.filename)
                    report_path = os.path.join('static/uploads', report_filename)
                    
                    with open(report_path, "wb") as f:
                        content = await report_file.read()
                        f.write(content)
                    
                    file_paths.append(report_path)
                    
                    file_size = os.path.getsize(report_path)
                    
                    c.execute("SELECT realname FROM users WHERE username = ?", (user["username"],))
                    uploader_realname_result = c.fetchone()
                    uploader_realname = uploader_realname_result[0] if uploader_realname_result else user["username"]
                    
                    upload_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    c.execute("""
                        INSERT INTO report_files 
                        (report_id, file_path, file_name, uploader_username, uploader_realname, upload_time, file_size)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        report_id, report_path, report_file.filename, user["username"],
                        uploader_realname, upload_time, file_size
                    ))
            
            if file_paths:
                all_files = existing_files + "," + ",".join(file_paths) if existing_files else ",".join(file_paths)
            else:
                all_files = existing_files
            
            final_reviewer1 = reviewer1 if reviewer1 is not None else existing_reviewer1
            final_reviewer2 = reviewer2 if reviewer2 is not None else existing_reviewer2
            final_reviewer3 = reviewer3 if reviewer3 is not None else existing_reviewer3
            final_signer1 = signer1 if signer1 is not None else existing_signer1
            final_signer2 = signer2 if signer2 is not None else existing_signer2
            
            reviewers = [final_reviewer1, final_reviewer2, final_reviewer3]
            if not all(reviewers):
                raise HTTPException(status_code=400, detail="必须设置3个复核人，不能有空缺")
            
            if len(reviewers) != len(set(reviewers)):
                raise HTTPException(status_code=400, detail="复核人不能重复，请选择3个不同的复核人")
            
            signers = [final_signer1, final_signer2]
            if not all(signers):
                raise HTTPException(status_code=400, detail="必须设置2个签字人，不能有空缺")
            
            if len(signers) != len(set(signers)):
                raise HTTPException(status_code=400, detail="签字人不能重复，请选择2个不同的签字人")
            
            c.execute("""
                UPDATE reports 
                SET reviewer1 = ?, reviewer2 = ?, reviewer3 = ?, 
                    signer1 = ?, signer2 = ?, file_paths = ?
                WHERE report_no = ? AND project_id = ?
            """, (
                final_reviewer1, final_reviewer2, final_reviewer3,
                final_signer1, final_signer2, all_files,
                report_no, project_id
            ))
            
            db.commit()
            return RedirectResponse(url=f"/project/{project_id}", status_code=303)
            
        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"更新报告失败: {str(e)}")

    async def generate_report_no(self, project_id, report_type, is_filing, reviewer1, reviewer2,
                           reviewer3, signer1, signer2, user, db):
        try:
            c = db.cursor()
            c.execute("SELECT status FROM projects WHERE id = ?", (project_id,))
            result = c.fetchone()
            
            if not result:
                raise HTTPException(status_code=404, detail="项目不存在")
            
            status = result[0]
            if status != 'active':
                raise HTTPException(status_code=400, detail="只有进行中的项目可以生成报告号")
            
            # 移除权限限制：所有人都可以为进行中的项目生成报告号
            # 只检查项目状态，不检查用户权限
            
            reviewers = [reviewer1, reviewer2, reviewer3]
            if len(reviewers) != len(set(reviewers)):
                raise HTTPException(status_code=400, detail="复核人不能重复，请选择3个不同的复核人")
            
            signers = [signer1, signer2]
            if len(signers) != len(set(signers)):
                raise HTTPException(status_code=400, detail="签字人不能重复，请选择2个不同的签字人")
            
            now = datetime.now()
            current_year = now.year
            current_month = now.strftime("%m")
            
            report_type_prefixes = {
                "房地产咨询报告": "房咨",
                "房地产估价报告": "房估",
                "资产评估报告": "评报",
                "资产估值报告": "估评",
                "资产咨询报告": "咨评",
                "土地报告": "土估"
            }
            
            filing_required_types = ["房地产估价报告", "资产评估报告", "土地报告"]
            
            if report_type not in report_type_prefixes:
                raise HTTPException(status_code=400, detail="无效的报告类型")
            
            if report_type in filing_required_types and not is_filing:
                raise HTTPException(status_code=400, detail=f"{report_type}需要选择是否备案")
            
            report_prefix = report_type_prefixes[report_type]
            year_pattern = f"[{current_year}]字第"
            
            if report_type in filing_required_types and is_filing == "是":
                pattern = f"%{report_prefix}{year_pattern}A{current_month}%"
            else:
                pattern = f"%{report_prefix}{year_pattern}{current_month}%"
            
            c.execute("""
                SELECT report_no FROM reports 
                WHERE report_no LIKE ? AND project_id = ?
            """, (pattern, project_id))
            
            existing_reports = c.fetchall()
            
            existing_numbers = []
            for report in existing_reports:
                report_no = report[0]
                if report_type in filing_required_types and is_filing == "是":
                    prefix_len = len(f"川鼎{report_prefix}{year_pattern}A{current_month}")
                    number_part = report_no[prefix_len:-1]
                else:
                    prefix_len = len(f"川鼎{report_prefix}{year_pattern}{current_month}")
                    number_part = report_no[prefix_len:-1]
                
                if number_part.isdigit():
                    existing_numbers.append(int(number_part))
            
            next_number = 1
            while next_number in existing_numbers:
                next_number += 1
            
            sequence_no = f"{next_number:03d}"
            
            prefix = "川鼎"
            middle = f"[{current_year}]字第"
            
            if report_type in filing_required_types and is_filing == "是":
                suffix = f"A{current_month}{sequence_no}号"
            else:
                suffix = f"{current_month}{sequence_no}号"
            
            report_no = f"{prefix}{report_type_prefixes[report_type]}{middle}{suffix}"
            
            create_date = now.strftime("%Y-%m-%d %H:%M:%S")
            
            # 获取当前用户的真实姓名
            c.execute("SELECT realname FROM users WHERE username = ?", (user["username"],))
            creator_realname_result = c.fetchone()
            creator_realname = creator_realname_result[0] if creator_realname_result else user["username"]
            
            c.execute("""
                INSERT INTO reports (
                    report_no, project_id, file_paths, creator, creator_realname, create_date,
                    reviewer1, reviewer2, reviewer3, signer1, signer2
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                report_no, project_id, "", user["username"], creator_realname, create_date,
                reviewer1, reviewer2, reviewer3, signer1, signer2
            ))
            
            c.execute("SELECT report_numbers FROM projects WHERE id = ?", (project_id,))
            result = c.fetchone()
            existing_report_numbers = result[0] if result and result[0] else ""
            
            if existing_report_numbers:
                new_report_numbers = existing_report_numbers + "," + report_no
            else:
                new_report_numbers = report_no
            
            c.execute("UPDATE projects SET report_numbers = ? WHERE id = ?", (new_report_numbers, project_id))
            
            db.commit()
            
            return {"report_no": report_no}
            
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"生成报告号失败: {str(e)}")

    async def delete_report(self, project_id, report_no, user, db):
        try:
            c = db.cursor()
            
            c.execute("SELECT status FROM projects WHERE id = ?", (project_id,))
            result = c.fetchone()
            
            if not result:
                raise HTTPException(status_code=404, detail="项目不存在")
            
            status = result[0]
            if status != 'active':
                raise HTTPException(status_code=400, detail="只有进行中的项目可以删除报告")
            
            # 获取报告信息，包括创建人
            c.execute("SELECT id, file_paths, creator FROM reports WHERE report_no = ? AND project_id = ?", (report_no, project_id))
            result = c.fetchone()
            
            if not result:
                raise HTTPException(status_code=404, detail="报告不存在")
            
            report_id = result[0]
            file_paths = result[1]
            report_creator = result[2]
            
            # 权限验证：只有管理员、项目创建人、项目负责人或报告创建人可以删除
            c.execute("SELECT creator, project_leader FROM projects WHERE id = ?", (project_id,))
            project_result = c.fetchone()
            if not project_result:
                raise HTTPException(status_code=404, detail="项目不存在")
            
            project_creator = project_result[0]
            project_leader = project_result[1]
            
            if not self.__check_report_permission(user, project_creator, project_leader, report_creator):
                raise HTTPException(status_code=403, detail="没有权限删除此报告")
            
            # 获取报告的所有文件信息（从 report_files 表）
            c.execute("SELECT file_path FROM report_files WHERE report_id = ?", (report_id,))
            file_records = c.fetchall()
            
            # 删除物理文件（从 report_files 表获取的文件路径）
            for file_record in file_records:
                file_path = file_record[0]
                if file_path and os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        print(f"🗑️ 已删除文件: {file_path}")
                    except Exception as e:
                        print(f"⚠️ 删除文件失败 {file_path}: {e}")
            
            # 同时删除原有的文件路径中的文件（为了兼容性）
            if file_paths:
                for file_path in file_paths.split(','):
                    if file_path.strip() and os.path.exists(file_path.strip()):
                        try:
                            os.remove(file_path.strip())
                            print(f"🗑️ 已删除文件: {file_path.strip()}")
                        except Exception as e:
                            print(f"⚠️ 删除文件失败 {file_path.strip()}: {e}")
            
            # 删除 report_files 表中的文件记录
            c.execute("DELETE FROM report_files WHERE report_id = ?", (report_id,))
            
            # 从 reports 表中删除报告记录
            c.execute("DELETE FROM reports WHERE report_no = ? AND project_id = ?", (report_no, project_id))
            
            # 更新项目的 report_numbers 字段
            c.execute("SELECT report_numbers FROM projects WHERE id = ?", (project_id,))
            result = c.fetchone()
            
            if result and result[0]:
                existing_report_numbers = result[0]
                # 从报告号列表中移除被删除的报告号
                report_list = existing_report_numbers.split(',')
                if report_no in report_list:
                    report_list.remove(report_no)
                    new_report_numbers = ','.join(report_list) if report_list else ""
                    c.execute("UPDATE projects SET report_numbers = ? WHERE id = ?", (new_report_numbers, project_id))
            
            db.commit()
            
            return RedirectResponse(url=f"/project/{project_id}", status_code=303)
            
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"删除报告失败: {str(e)}")
    async def delete_report_file(self, project_id, report_id, file_id, user, db):
        """删除报告文件"""
        try:
            c = db.cursor()
            
            # 检查项目状态
            c.execute("SELECT status FROM projects WHERE id = ?", (project_id,))
            result = c.fetchone()
            
            if not result:
                raise HTTPException(status_code=404, detail="项目不存在")
            
            status = result[0]
            if status != 'active':
                raise HTTPException(status_code=400, detail="只有进行中的项目可以删除文件")
            
            # 获取报告信息
            c.execute("SELECT id, creator, project_id FROM reports WHERE id = ?", (report_id,))
            report_result = c.fetchone()
            
            if not report_result:
                raise HTTPException(status_code=404, detail="报告不存在")
            
            report_creator = report_result[1]
            report_project_id = report_result[2]
            
            # 检查项目权限
            c.execute("SELECT creator, project_leader FROM projects WHERE id = ?", (report_project_id,))
            project_result = c.fetchone()
            
            if not project_result:
                raise HTTPException(status_code=404, detail="项目不存在")
            
            project_creator = project_result[0]
            project_leader = project_result[1]
            
            # 权限验证：管理员、报告创建人
            has_permission = self.__check_report_permission(user, project_creator, project_leader, report_creator)
            
            if not has_permission:
                raise HTTPException(status_code=403, detail="没有权限删除此文件")
            
            # 获取文件信息
            c.execute("SELECT file_path FROM report_files WHERE id = ? AND report_id = ?", (file_id, report_id))
            file_result = c.fetchone()
            
            if not file_result:
                raise HTTPException(status_code=404, detail="文件不存在")
            
            file_path = file_result[0]
            
            # 删除物理文件
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    print(f"🗑️ 已删除文件: {file_path}")
                except Exception as e:
                    print(f"⚠️ 删除文件失败 {file_path}: {e}")
            
            # 从数据库删除文件记录
            c.execute("DELETE FROM report_files WHERE id = ? AND report_id = ?", (file_id, report_id))
            
            # 更新报告的 file_paths 字段（为了兼容性）
            c.execute("SELECT file_paths FROM reports WHERE id = ?", (report_id,))
            report_file_paths = c.fetchone()
            
            if report_file_paths and report_file_paths[0]:
                file_paths_list = report_file_paths[0].split(',')
                if file_path in file_paths_list:
                    file_paths_list.remove(file_path)
                    new_file_paths = ','.join(file_paths_list) if file_paths_list else ""
                    c.execute("UPDATE reports SET file_paths = ? WHERE id = ?", (new_file_paths, report_id))
            
            db.commit()
            
            return RedirectResponse(url=f"/project/{project_id}", status_code=303)
            
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"删除文件失败: {str(e)}")