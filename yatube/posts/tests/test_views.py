import shutil
import tempfile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.conf import settings
from django import forms
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile

from posts.models import Post, Group, User, Comment, Follow
from posts.forms import PostForm, CommentForm
from yatube.settings import PAGE_SIZE

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username='Tanos')
        cls.group = Group.objects.create(
            title='Первая группа',
            slug='test-slug',
            description='Описание группы'
        )
        cls.group_2 = Group.objects.create(
            title='Вторая группа',
            slug='test-slug2',
            description='Описание группы 2'
        )
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            group=cls.group,
            text='Пост номер 1',
            image=uploaded
        )
        cls.comment = Comment.objects.create(
            author=cls.user, post=cls.post, text='Комментарий 1'
        )
        cls.url_names = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': f'{cls.group.slug}'}),
            reverse('posts:profile', kwargs={'username': f'{cls.user}'})
        ]

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list', kwargs={'slug': 'test-slug'}): (
                'posts/group_list.html'
            ),
            reverse('posts:profile', kwargs={'username': 'Tanos'}): (
                'posts/profile.html'
            ),
            reverse('posts:post_detail', kwargs={'post_id': 1}): (
                'posts/post_detail.html'
            ),
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:post_edit', kwargs={'post_id': 1}): (
                'posts/create_post.html'
            ),
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def assert_context_post(self, context):
        self.assertIn('page_obj', context)
        page_obj = context['page_obj']
        post = page_obj[0]
        self.assertIsInstance(post, Post)
        self.assertEqual(self.post.text, post.text)
        self.assertEqual(self.post.group, post.group)
        self.assertEqual(self.post.pub_date, post.pub_date)
        self.assertEqual(self.post.author, post.author)
        self.assertEqual(self.post.image, post.image)

    def test_index_page_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:index'))
        self.assert_context_post(response.context)

    def test_group_page_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': 'test-slug'})
        )
        self.assertIn('group', response.context)
        group = response.context['group']
        self.assertEqual(group, self.group)
        self.assertIn('page_obj', response.context)
        self.assertIsInstance(group, Group)
        self.assertEquals(group.title, self.group.title)
        self.assertEquals(group.slug, self.group.slug)
        self.assertEquals(group.description, self.group.description)

    def test_profile_page_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': 'Tanos'})
        )
        self.assertIn('author', response.context)
        author = response.context['author']
        self.assertEqual(author, self.user)
        self.assertIsInstance(author, User)
        self.assertEqual(author.username, self.user.username)
        self.assert_context_post(response.context)
        following = response.context['following']
        self.assertIsInstance(following, bool)
        self.assertEqual(following, False)

    def test_post_detail_page_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': (self.post.pk)})
        )
        self.assertIn('post', response.context)
        post = response.context['post']
        self.assertIsInstance(post, Post)
        self.assertEqual(self.post.text, post.text)
        self.assertEqual(self.post.group, post.group)
        self.assertEqual(self.post.pub_date, post.pub_date)
        self.assertEqual(self.post.author, post.author)
        form = response.context['form']
        self.assertIsInstance(form, CommentForm)
        form_field = form.fields.get('text')
        self.assertIsInstance(form_field, forms.fields.CharField)
        comments = response.context['comments']
        self.assertEqual(comments[0], self.comment)

    def test_post_create_page_show_correct_context(self):
        """Шаблон post_create сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form = response.context.get('form')
        self.assertIsInstance(form, PostForm)
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = form.fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_edit_page_show_correct_context(self):
        """Шаблон post_edit сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse(
            'posts:post_edit', args=(self.post.pk,)))
        form = response.context.get('form')
        self.assertIsInstance(form, PostForm)
        self.assertEqual(response.context['is_edit'], True)
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = form.fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_new_post_is_shown(self):
        """При создании в группе, то этот пост появляется:
        главная страница,
        страница выбранной группы,
        профайл пользователя.
        """
        new_post = Post.objects.create(
            text='Новый пост 2',
            author=self.user,
            group=self.group,
        )
        urls = [
            reverse('posts:index'),
            reverse('posts:profile', kwargs={'username': self.user.username}),
            reverse('posts:group_list', kwargs={'slug': self.group.slug})
        ]
        for url in urls:
            with self.subTest(value=url):
                response = self.guest_client.get(url)
                self.assertIn(new_post, response.context['page_obj'])

    def test_new_post_for_your_group(self):
        """Проверка, что пост не попал в группу,
        для которой не был предназначен.
        """
        new_post = Post.objects.create(
            text='Новый пост 2',
            author=self.user,
            group=self.group,
        )
        response = self.guest_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group_2.slug})
        )
        self.assertNotIn(new_post, response.context['page_obj'])

    def test_check_cache(self):
        """Проверка кеша."""
        response = self.guest_client.get(reverse("posts:index"))
        _before_delete = response.content
        Post.objects.get(id=1).delete()
        response2 = self.guest_client.get(reverse("posts:index"))
        _after_delete = response2.content
        self.assertEqual(_before_delete, _after_delete)
        cache.clear()
        self.assertNotEqual(_after_delete, self.guest_client.get(
            reverse('posts:index')
        ).content)


class FollowTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username='Rocket Racoon')
        cls.author = User.objects.create(username='Tanos')

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.post = Post.objects.create(text='Тестовый пост',
                                       author=self.user)

    def test_authorized_client_can_follow(self):
        """Авторизованный пользователь может подписываться."""
        follow = Follow.objects.filter(
            user=self.user, author=self.author).exists()
        self.assertEqual(follow, False)
        self.authorized_client.get(
            reverse('posts:profile_follow',
                    kwargs={'username': self.author})
        )
        follow = Follow.objects.filter(
            user=self.user, author=self.author).exists()
        self.assertEqual(follow, True)

    def test_not_authorized_client_cannot_follow(self):
        """Неавторизованный пользователь не может подписываться."""
        follow = Follow.objects.all().count()
        response = self.guest_client.get(
            reverse('posts:profile_follow',
                    kwargs={'username': self.author})
        )
        self.assertRedirects(response,
                             reverse
                             ('users:login') + '?next='
                             + f'/profile/{self.author}/follow/')
        new_follow = Follow.objects.all().count()
        self.assertEqual(follow, new_follow)

    def test_authorized_client_cannot_follow_twice(self):
        """Проверка уникальности подписки авторизованного пользователя
         (вызов метода get_or_create во view-функции)."""
        self.authorized_client.get(
            reverse('posts:profile_follow',
                    kwargs={'username': self.author})
        )
        follow = Follow.objects.filter(
            user=self.user, author=self.author).count()
        self.assertEqual(follow, 1)
        self.authorized_client.get(
            reverse('posts:profile_follow',
                    kwargs={'username': self.author})
        )
        follow = Follow.objects.filter(
            user=self.user, author=self.author).count()
        self.assertEqual(follow, 1)

    def test_authorized_client_can_unfollow(self):
        """Только авторизованный пользователь может отписываться."""
        follow = Follow.objects.all().count()
        Follow.objects.create(user=self.user, author=self.author)
        self.authorized_client.get(
            reverse('posts:profile_unfollow',
                    kwargs={'username': self.author})
        )
        new_follow = Follow.objects.all().count()
        self.assertEqual(follow, new_follow)

    def test_new_post_for_follower(self):
        """В ленте подписчика появляется новая запись автора,
         на которого он подписан."""
        Follow.objects.create(user=self.user, author=self.author)
        author_post = Post.objects.create(
            text='Пост для ленты',
            author=self.author
        )
        Post.objects.create(text='Пост для главной', author=self.user)
        response = self.authorized_client.get(reverse('posts:follow_index'))
        self.assertIn(author_post, response.context['page_obj'])

    def test_new_post_for_not_follower(self):
        """Новая запись автора не появляется к ленте тех,
         кто на него не подписан."""
        author_post = Post.objects.create(text='Пост для ленты', author=self.author)
        response = self.authorized_client.get(reverse('posts:follow_index'))
        self.assertNotIn(author_post, response.context['page_obj'])


class PaginatorTest(TestCase):
    SECOND_PAGE_AMOUNT = PAGE_SIZE // 2

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username='Tanos')
        cls.group = Group.objects.create(
            title='Первая группа',
            slug='test-slug',
            description='Описание группы'
        )

        batch_size = PAGE_SIZE + cls.SECOND_PAGE_AMOUNT
        posts = []
        for _ in range(batch_size):
            post = Post(
                text='Записи группы',
                author=cls.user,
                group=cls.group
            )
            posts.append(post)
        Post.objects.bulk_create(posts, batch_size)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_paginator_first_page_contains_ten_records(self):
        urls = [
            reverse('posts:index'),
            reverse('posts:profile', kwargs={'username': self.user.username}),
            reverse('posts:group_list', kwargs={'slug': self.group.slug})
        ]
        for url in urls:
            with self.subTest(value=url):
                response = self.guest_client.get(url)
                self.assertEqual(len(response.context['page_obj']), PAGE_SIZE)
                response = self.guest_client.get(url + '?page=2')
                self.assertEqual(len(response.context['page_obj']),
                                 self.SECOND_PAGE_AMOUNT)
