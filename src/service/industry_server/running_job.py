from tqdm import tqdm

from ..database_server.model import IndustryJobs as M_IndustryJobs, IndustryJobsCache as M_IndustryJobsCache
from ..character_server.character import Character
from ..evesso_server.eveesi import characters_character_id_industry_jobs, corporations_corporation_id_industry_jobs
from ..evesso_server.eveutils import find_max_page, get_multipages_result
from ..database_server.connect import db

# kahuna logger
from ..log_server import logger

class RunningJobOwner:
    @classmethod
    def refresh_character_running_job(cls, character: Character):
        character_running_job = characters_character_id_industry_jobs(character.ac_token, character.character_id)
        if not character_running_job:
            return

        for data in character_running_job:
            data['location_id'] = data['station_id']
            data.pop('station_id')
            data.update({'owner_id': character.character_id})
        with db.atomic():
            M_IndustryJobs.delete().where(M_IndustryJobs.owner_id == character.character_id).execute()
            M_IndustryJobs.insert_many(character_running_job).execute()

    @classmethod
    def refresh_corp_running_job(cls, corp_id, character: Character):
        max_page = find_max_page(corporations_corporation_id_industry_jobs, character.ac_token, corp_id,
                                 begin_page=1, interval=2)
        logger.info("请求刷新进行中job。")
        results = get_multipages_result(corporations_corporation_id_industry_jobs, max_page, character.ac_token, corp_id)

        with db.atomic():
            M_IndustryJobs.delete().where(M_IndustryJobs.owner_id == corp_id).execute()
            with tqdm(total=len(results), desc="写入数据库", unit="page", ascii='=-') as pbar:
                for result in results:
                    for jobs in result:
                        jobs.update({'owner_id': corp_id})
                    M_IndustryJobs.insert_many(result).execute()

    @classmethod
    def copy_to_cache(cls):
        M_IndustryJobsCache.delete().execute()
        db.execute_sql(
            f"INSERT INTO {M_IndustryJobsCache._meta.table_name} SELECT * FROM {M_IndustryJobs._meta.table_name}")
        logger.info("copy data to cache complete")

    @classmethod
    def get_job_with_starter(cls, character_id_list: list):
        res = M_IndustryJobsCache.select().where(M_IndustryJobsCache.installer_id.in_(character_id_list))

        return res

    @classmethod
    def get_using_bp_set(cls):
        res = M_IndustryJobsCache.select(M_IndustryJobsCache.blueprint_id)
        bp_set = set()
        for job in res:
            bp_set.add(job.blueprint_id)

        return bp_set