# coding:utf-8
from app.cache import hot_post_cache, system_status_cache, topic_category_cache

from custor.handlers.basehandler import BaseRequestHandler
from custor.decorators import timeit, exception_deal, check_captcha
from custor.utils import get_cleaned_post_data, get_cleaned_query_data
from custor.utils import json_result, get_page_nav, get_page_number

from db.mysql_model.post import Post, PostTopic
from db.mysql_model.user import User

from custor.errors import RequestMissArgumentError, PageNotFoundError

from settings.config import config


class IndexHandler(BaseRequestHandler):
    """
    社区首页
    """
    # 时间消耗装饰器
    @timeit
    # 异常捕获装饰器
    @exception_deal([RequestMissArgumentError,]) # 也许这个参数有其他用处先留着
    def get(self, *args, **kwargs):
        # profiling 性能分析
        # from profiling.tracing import TracingProfiler
        #
        # # profile your program.
        # profiler = TracingProfiler()
        # profiler.start()

        current_page = get_cleaned_query_data(self, ['page',], blank=True)['page']
        current_page = get_page_number(current_page)
        posts, page_number_limit = Post.list_recently(page_number=current_page)
        pages = get_page_nav(current_page, page_number_limit, config.default_page_limit)
        self.render('index/index.html',
                    posts=posts,
                    topic_category_cache=topic_category_cache,
                    hot_post_cache=hot_post_cache,
                    systatus=system_status_cache,
                    current_topic=None,
                    pages=pages,
                    pages_prefix_url='/?page=')

        # profiler.stop()
        # profiler.run_viewer()


class IndexTopicHandler(BaseRequestHandler):
    """
    带分类的首页
    """
    def get(self, topic_id, *args, **kwargs):
        try:
            topic = PostTopic.get(PostTopic.str == topic_id)
        except PostTopic.DoesNotExist:
            self.redirect("/static/404.html")
            return
        current_page = get_cleaned_query_data(self, ['page',], blank=True)['page']
        if current_page:
            current_page = int(current_page)
            if current_page < 1:
                self.redirect("/static/404.html")
                return
            posts, page_number_limit = Post.list_by_topic(topic, page_number=current_page)
        else:
            current_page = 1
            posts, page_number_limit = Post.list_by_topic(topic)
        pages = get_page_nav(current_page, page_number_limit, config.default_page_limit)
        self.render('index/index.html',
                    posts=posts,
                    topic_category_cache=topic_category_cache,
                    hot_post_cache=hot_post_cache,
                    systatus=system_status_cache,
                    current_topic=topic,
                    pages=pages,
                    pages_prefix_url='/topic/'+topic.str+'?page=')


class RegisterHandler(BaseRequestHandler):
    """
    用户注册操作
    """
    def get(self, *args, **kwargs):
        if self.current_user:
            self.redirect('/')
        else:
            self.render('index/register.html')

    def post(self, *args, **kwargs):
        post_data = get_cleaned_post_data(self, ['username', 'email', 'password'])
        if User.get_by_username(username=post_data['username']):
            self.write(json_result(1, '用户名经存在'))
            return

        if User.get_by_email(email=post_data['email']):
            self.write(json_result(1, '邮箱已经存在'))
            return

        user = User.new(username=post_data['username'],
                 email=post_data['email'],
                 password=post_data['password'])
        self.write(json_result(0,{'username': user.username}))

class LoginHandler(BaseRequestHandler):
    """
    用户登陆
    """
    def get(self, *args, **kwargs):
        if self.current_user:
            self.redirect('/')
        else:
            self.render('index/login.html')

    @timeit
    @exception_deal([RequestMissArgumentError,]) # 也许这个参数有其他用处先留着
    @check_captcha(-4, '验证码错误') # 检查验证码,返回(错误码, 错误信息)
    def post(self, *args, **kwargs):
        post_data = get_cleaned_post_data(self, ['username', 'password'])
        user = User.auth(post_data['username'], post_data['password'])
        if user:
            self.set_secure_cookie('uuid', user.username)
            result = json_result(0, 'login success!')
        else:
            result = json_result(-1, 'login failed!')
        self.write(result)

class LogoutHandler(BaseRequestHandler):
    """
    用户登出
    """
    def get(self, *args, **kwargs):
        if self.current_user:
            self.clear_cookie('uuid')
        self.redirect('/')
