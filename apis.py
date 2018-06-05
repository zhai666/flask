import uuid

import os
from flask import request, session
from flask_restful import Api, Resource, marshal_with, fields, marshal, reqparse
from sqlalchemy import or_
from werkzeug.datastructures import FileStorage

import settings
from models import User, Image, Music
from dao import query, queryAll, add, delete, queryById, deleteById

api = Api()


def init_api(app):
    api.init_app(app)


class UserApi(Resource):  # 声明User资源
    def get(self):
        # 读取请求参数中的key
        key = request.args.get('key')
        if key:
            result = {'state': 'fail',
                      'msg': '查无数据'}
            # 搜索用户信息 key ＝ id/name/phone
            qs = query(User).filter(or_(User.id == key,
                                        User.name == key,
                                        User.phone == key))
            if qs.count():
                result['state'] = 'ok'
                result['msg'] = '查询成功'
                result['data'] = qs.first().json

            return result

        # 从数据库中查询所有的用户
        users = queryAll(User)

        return {'state': 'ok',
                'data': [user.json for user in users]}

    def post(self):
        # 从上传的form对象中取出name和phone
        name = request.form.get('name')
        phone = request.form.get('phone')

        print(name, phone)
        # 数据存入到数据库
        user = User()
        user.name = name
        user.phone = phone

        add(user)  # 添加到数据库

        return {"state": "ok",
                "msg": '添加 {} 用户成功!'.format(name)}

    def delete(self):
        id = request.args.get('id')  # id -> str
        # user = queryById(User, id)  # 是否考虑 id 不存在的情况
        # delete(user)

        flag = deleteById(User, id)

        return {'state': 'ok',
                'flag': flag,
                'msg': '删除 {} 成功!'.format(id)}

    def put(self):
        id = request.form.get('id')
        user = queryById(User, id)
        user.name = request.form.get('name')
        user.phone = request.form.get('phone')

        add(user)

        return {'state':'ok',
                'msg': user.name+'更新成功！'}

class ImageApi(Resource):

    # 设置图片Image对象输出的字段
    img_fields = {"id": fields.Integer,
                  "name": fields.String,
                  # "img_url": fields.String(attribute='url'),
                  "url": fields.String,
                  "size": fields.Integer(default=0)}
    get_out_fields = {
        "state": fields.String(default='ok'),
        "data": fields.Nested(img_fields),
        "size": fields.Integer(default=1)
    }

    # @marshal_with(get_out_fields)
    def get(self):

        id = request.args.get('id')
        if id:
            img = query(Image).filter(Image.id == id).first()

            # 将对象转成输出的字段格式（json格式）
            return marshal(img, self.img_fields)
        else:
            # 查询所有Image
            images = queryAll(Image)
            data = {"data": images,
                    "size": len(images)}

            # 向session中存放用户名
            session['login_name'] = 'disen'

            return marshal(data, self.get_out_fields)

    parser = reqparse.RequestParser()
    parser.add_argument('name',required=True, help='必须提供图片名称参数')
    parser.add_argument('url', required=True, help='必须提供已上传图片的路径')
    def post(self):
        args = self.parser.parse_args()

        # 保存数据
        img = Image()
        img.name = args.get('name')
        img.url = args.get('url')

        add(img)  # 添加到数据库中

        return {'msg':'添加图片成功!'}

class MusicApi(Resource):

    # 创建request参数的解析器
    parser = reqparse.RequestParser()

    # 向参数解析器中添加请求参数说明
    parser.add_argument('key', dest='name', type=str, required=True, help='必须提供name搜索的关键字')
    parser.add_argument('id', type=int, help='请确定id的参数是否为数值类型?')
    parser.add_argument('tag', action='append', required=True, help='至少提供一个tag标签')
    parser.add_argument('session', location='cookies', required=True, help='cookie中不存在session')


    # 定制输出
    music_fields = {
        'id': fields.Integer,
        'name': fields.String,
        'singer': fields.String,
        'url': fields.String(attribute='mp3_url')
    }

    out_fields = {
        'state': fields.String(default='ok'),
        'msg': fields.String(default='查询成功'),
        'data': fields.Nested(music_fields)
    }

    @marshal_with(out_fields)
    def get(self):
        # 按name 搜索
        # 通过request参数解析器，开始解析请求参数
        # 如果请求参数不能满足条件，则直接返回参数相关的help说明
        args = self.parser.parse_args()

        # 从 args中读取name请求参数的值
        name = args.get('name')
        tags = args.get('tag')

        # 从args 中读取session(cookies的session)
        session = args.get('session')
        print('session->>', session)

        musics = query(Music).filter(Music.name.like('%{}%'.format(name)))
        if musics.count():
            return {'data': musics.all()}

        return {'msg': '搜索 {} 音乐不存在, 标签： {}'.format(name, tags)}



class UploadApi(Resource):

    # 定制输入的参数
    parser = reqparse.RequestParser()
    parser.add_argument("img",
                        type=FileStorage,
                        location='files',
                        required=True,
                        help='必须提供一个名为img的File表单参数')

    def post(self):
        # 验证 请求参数是否满足条件
        args = self.parser.parse_args()

        # 保存上传的文件
        uFile:FileStorage = args.get('img')
        print('上传的文件名:', uFile.filename)

        newFileName = str(uuid.uuid4()).replace('-', '')
        newFileName += "."+ uFile.filename.split('.')[-1]

        uFile.save(os.path.join(settings.MEDIA_DIR, newFileName))

        return {'msg':'上传成功!',
                'path':'/static/uploads/{}'.format(newFileName)}


# 将资源添加到api对象中，并声明uri
# -------------------------------
api.add_resource(UserApi, '/user/')
api.add_resource(ImageApi, '/images/')
api.add_resource(MusicApi, '/music/')
api.add_resource(UploadApi, '/upload/')
