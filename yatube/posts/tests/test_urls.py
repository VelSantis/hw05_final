from http import HTTPStatus
from django.urls import reverse
from django.test import Client, TestCase

from posts.models import Group, Post, User


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username='Tanos')
        cls.user2 = User.objects.create(username='Locki')
        cls.post = Post.objects.create(
            text='Тестовая запись',
            author=cls.user,
        )
        cls.post2 = Post.objects.create(
            text='Тестовая запись',
            author=cls.user2,
        )
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Описание группы',
        )

        cls.public_urls = {
            '/': 'posts/index.html',
            f'/group/{cls.group.slug}/': 'posts/group_list.html',
            f'/profile/{cls.post.author}/': 'posts/profile.html',
            f'/posts/{cls.post.id}/': 'posts/post_detail.html',
        }
        cls.private_urls = {
            '/create/': 'posts/create_post.html',
            f'/posts/{cls.post.id}/edit/': 'posts/create_post.html',
        }
        cls.all_urls = {
            **cls.public_urls, **cls.private_urls
        }

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_public_urls_accessed_by_guest(self):
        """Страница доступна любому пользователю."""
        for address, template in PostURLTests.public_urls.items():
            with self.subTest(address=address):
                response = self.guest_client.get(address)
                self.assertTemplateUsed(response, template)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_all_urls_accessed_by_authorized_client(self):
        """Страницы доступны авторизованному пользователю."""
        for address, template in PostURLTests.all_urls.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_private_urls_redirect_guest(self):
        """Проверяем переадресацию для анонимного
        пользователя с приватных страниц.
        """
        for address in PostURLTests.private_urls:
            with self.subTest(address=address):
                response = self.guest_client.get(address)
                self.assertRedirects(response,
                                     reverse
                                     ('users:login') + '?next=' + address)

    def test_bad_user_redirect_on_edit(self):
        """Проверяем переадресацию для авторизованного пользователя
        при редактировании чужого поста.
        """
        post_id = PostURLTests.post2.id
        response = self.authorized_client.get(
            reverse('posts:post_edit', kwargs={'post_id': post_id})
        )
        self.assertRedirects(response,
                             reverse('posts:post_detail', args=(post_id,)))

    def test_unexisting_page_returns_404(self):
        """Запрос к несуществующей странице."""
        response = self.client.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
