import pandas as pd
from ..utils.util import model_dicL


# def create_table(engine, model_list):
#     Obj = model_list[0]
#     Obj.__table__.create(engine)


def bulk_save(session, model_list):
    try:
        session.bulk_save_objects(model_list,update_changed_only=False)
        session.commit()
    except Exception as e:
        # print(e)
        session.rollback()
        pass


def bulk_update(session, obj, model_list):
    try:
        list = model_dicL(model_list)
        session.bulk_update_mappings(obj, list)
        session.commit()
    except Exception as e:
        # print(e)
        session.rollback()
        pass


def bulk_insert(session, obj, model_list):
    try:
        list = model_dicL(model_list)
        session.bulk_insert_mappings(obj, list)
        session.commit()
    except Exception as e:
        # print(e)
        session.rollback()
        pass


def insert_onebyone(session, model_list):
    for model in model_list:
        try:
            session.add(model)
            session.commit()
        except Exception as e:
            # print(e)
            session.rollback()
            pass
