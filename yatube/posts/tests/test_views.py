from http import HTTPStatus
from django.test import Client, TestCase
from django.urls import reverse
from django import forms
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache

from posts.models import Post, Group, User, Comment, Follow
from posts.forms import PostForm
from yatube.settings import PAGE_SIZE


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
        cls.post = Post.objects.create(
            author=cls.user,
            group=cls.group,
            text='Пост номер 1'
        )
        cls.url_names = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': f'{cls.group.slug}'}),
            reverse('posts:profile', kwargs={'username': f'{cls.user}'})
        ]

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

    def test_new_post_with_pictures_in_right_place(self):
        """Новый пост с img есть на страницах index, group, profile, detail"""
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
        post_wth_pic = Post.objects.create(
            text='Новый текст с картинкой',
            author=self.user,
            group=self.group,
            image=uploaded,
        )
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': post_wth_pic.id})
        )
        self.assertEqual(response.context.get('post'), post_wth_pic)
        for name in self.url_names:
            with self.subTest(name=name):
                response = self.authorized_client.get(name)
                self.assertEqual(post_wth_pic, response.context['page_obj'][0])
                self.assertEqual(response.context['page_obj'][0].image,
                                 post_wth_pic.image.name)

    def test_comment_correct_context(self):
        """Валидная форма Комментария создает запись в Post."""
        comments_count = Comment.objects.count()
        form_data = {"text": "Тестовый коммент"}
        response = self.authorized_client.post(
            reverse("posts:add_comment", kwargs={"post_id": self.post.id}),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(
            response, reverse("posts:post_detail",
                              kwargs={"post_id": self.post.id})
        )
        self.assertEqual(Comment.objects.count(), comments_count + 1)
        self.assertTrue(Comment.objects.filter(text="Тестовый коммент")
                        .exists())

    def test_check_cache(self):
        """Проверка кеша."""
        response = self.guest_client.get(reverse("posts:index"))
        r_1 = response.content
        Post.objects.get(id=1).delete()
        response2 = self.guest_client.get(reverse("posts:index"))
        r_2 = response2.content
        self.assertEqual(r_1, r_2)
        cache.clear()
        self.assertNotEqual(r_2, self.guest_client.get(
            reverse('posts:index')
        ).content)

    def test_follow_page(self):
        """Проверяем, что страница подписок пуста.
        Проверка подписки на автора поста.
        Проверка подписки у юзера-фоловера.
        """
        response = self.authorized_client.get(reverse("posts:follow_index"))
        self.assertEqual(len(response.context["page_obj"]), 0)
        Follow.objects.get_or_create(user=self.user, author=self.post.author)
        r_2 = self.authorized_client.get(reverse("posts:follow_index"))
        self.assertEqual(len(r_2.context["page_obj"]), 1)
        self.assertIn(self.post, r_2.context["page_obj"])
        """Проверка что пост не появился в избранных у юзера-обычного."""
        outsider = User.objects.create(username="NoName")
        self.authorized_client.force_login(outsider)
        r_2 = self.authorized_client.get(reverse("posts:follow_index"))
        self.assertNotIn(self.post, r_2.context["page_obj"])
        """Проверка отписки от автора поста."""
        Follow.objects.all().delete()
        r_3 = self.authorized_client.get(reverse("posts:follow_index"))
        self.assertEqual(len(r_3.context["page_obj"]), 0)


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
