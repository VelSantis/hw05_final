from django.test import Client, TestCase
from django.urls import reverse

from posts.models import Group, Post, User


class PostCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='user')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Описание группы'
        )
        cls.post = Post.objects.create(
            text='Тестовая запись',
            author=cls.user,
            group=cls.group
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_create_post(self):
        """Валидная форма создает запись"""
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Тестовый текст',
            'group': self.group.pk,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, reverse(
            'posts:profile', kwargs={'username': PostCreateFormTests.user})
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertTrue(
            Post.objects.filter(
                group=PostCreateFormTests.group,
                author=PostCreateFormTests.user,
                text='Тестовый текст'
            ).exists()
        )

    def test_guest_create_post(self):
        """Создание записи только после авторизации"""
        post_count = Post.objects.count()
        form_data = {
            'text': 'Тестовый пост от неавторизованного пользователя',
            'group': self.group.pk,
        }
        Post.objects.create(
            text='Тестовый пост',
            group=Group.objects.get(title='Тестовая группа'),
            author=self.user
        )
        response = self.guest_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(
            response, f'{reverse("users:login")}?next=/create/'
        )
        self.assertFalse(
            Post.objects.filter(
                text='Тестовый пост от неавторизованного пользователя'
            ).exists()
        )
        self.assertEqual(Post.objects.count(), post_count + 1)

    def test_authorized_edit_post(self):
        """Редактирование записи создателем поста"""
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Изменённый текст',
            'group': self.group.id
        }
        response = self.authorized_client.post(
            reverse('posts:post_edit',
                    kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, reverse(
            'posts:post_detail',
            kwargs={'post_id': self.post.id},
        ))
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertEqual(
            Post.objects.get(id=self.post.id).text,
            form_data['text'],
        )
        self.assertEqual(
            Post.objects.get(id=self.post.id).group.id,
            form_data['group'],
        )
        self.assertEqual(
            Post.objects.get(id=self.post.id).author, self.user
        )
