import pytest
from backend import *
import random

class TestWatch:
    def test_watch_creation(self):
        Watch(None, None, None, None, None, None, None, None)

    def test_watch_init(self):
        i = random_bytes(8, 4)
        watch = Watch(i[0], i[1], i[2], i[3], i[4], i[5], i[6], i[7])
        assert watch.watch_id == i[0]
        assert watch.name == i[1]
        assert watch.brand == i[2]
        assert watch.price == i[3]
        assert watch.material == i[4]
        assert watch.reference == i[5]
        assert watch.condition == i[6]
        assert watch.image_url == i[7]

    def test_watch_get_details(self):
        i = random_bytes(8, 4)
        watch = Watch(i[0], i[1], i[2], i[3], i[4], i[5], i[6], i[7])
        assert watch.get_details() == {
            "watch_id": i[0],
            "name": i[1],
            "brand": i[2],
            "price": i[3],
            "material": i[4],
            "reference": i[5],
            "condition": i[6],
            "image_url": i[7],
        }

    def test_watch_string(self):
        i = random_bytes(8, 4)
        watch = Watch(i[0], i[1], i[2], i[3], i[4], i[5], i[6], i[7])
        assert str(watch) == f"{i[0]} - {i[1]} ({i[2]}) - ${i[3]}"

    def test_watch_large_data(self):
        i = random_bytes(8, 999999)
        Watch(i[0], i[1], i[2], i[3], i[4], i[5], i[6], i[7])

class TestUser:
    def test_user_creation(self):
        User(None, None, None, None)

    def test_user_init(self):
        i = random_bytes(3, 8)
        user = User(i[0], i[1], i[2])
        assert user.user_id == i[0]
        assert user.username == i[1]
        assert user.password_hash == i[2]

    def test_user_login_logout(self):
        i = random_bytes(3, 8)
        user = User(i[0], i[1], i[2])
        assert user.login(i[1], i[2])
        assert user.logged_in is True
        user.logout()
        assert user.logged_in is False
        assert user.login(i[1] + b"1", i[2]) is False

class TestCatalogue:
    def test_catalogue_creation(self):
        Catalogue()

    def test_catalogue_init(self):
        catalogue = Catalogue()
        assert len(catalogue.watches) == 0

    def test_catalogue_add_watch(self):
        catalogue, watchlist = self.create_test_catalogue(1)
        assert len(catalogue.watches) == 1
        assert catalogue.watches[0].name == watchlist[0].name
        catalogue.add_watch(watch_random_data(1))
        catalogue.add_watch(watch_random_data(2))
        assert len(catalogue.watches) == 3
        with pytest.raises(ValueError, match=f"Watch with ID {watchlist[0].watch_id} already exists."):
            catalogue.add_watch(watchlist[0])

    def test_catalogue_edit_watch(self):
        catalogue, watchlist = self.create_test_catalogue(2)
        x = random_bytes(8, 8)
        catalogue.edit_watch(0, name=x[1], material=x[4])
        for watch in catalogue.watches:
            if watch.watch_id == 0:
                assert watch.name == x[1]
                assert watch.material == x[4]
        watch_id = 3
        with pytest.raises(ValueError, match=f"Watch with ID {watch_id} not found."):
            catalogue.edit_watch(watch_id)

    def test_catalogue_delete_watch(self):
        catalogue, watchlist = self.create_test_catalogue(2)
        catalogue.delete_watch(1)
        assert len(catalogue.watches) == 1
        for checkwatch in catalogue.watches:
            assert checkwatch != watchlist[1]
        watch_id = 1
        with pytest.raises(ValueError, match=f"Watch with ID {watch_id} not found."):
            catalogue.delete_watch(watch_id)

    def test_catalogue_get_watch(self):
        catalogue, watchlist = self.create_test_catalogue(3)
        assert catalogue.get_watch(0) == watchlist[0]
        assert catalogue.get_watch(3) is None

    def test_catalogue_get_all_watches(self):
        catalogue, watchlist = self.create_test_catalogue(5)
        assert catalogue.watches == watchlist

    def test_catalogue_search_watches(self):
        pass

    @staticmethod
    def create_test_catalogue(watchamount):
        catalogue = Catalogue()
        watchlist = []
        for x in range(0, watchamount):
            watch = watch_random_data(x)
            watchlist.append(watch)
            catalogue.add_watch(watch)
        return catalogue, watchlist


class TestAdmin:
    def test_admin_creation(self):
        Admin(None, None, None)

    def test_admin_init(self):
        i = random_bytes(3, 8)
        admin = Admin(i[0], i[1], i[2])
        assert admin.user_id == i[0]
        assert admin.username == i[1]
        assert admin.password_hash == i[2]

    def test_admin_add_watch(self):
        catalogue = Catalogue()
        watch = watch_random_data(0)
        j = random_bytes(3, 8)
        admin = Admin(j[0], j[1], j[2])
        try:
            admin.add_watch(watch, catalogue)
            raise Exception
        except PermissionError:
            pass
        admin.login(j[1], j[2])
        try:
            admin.add_watch(watch, catalogue)
        except PermissionError:
            raise Exception

class TestSessionManager:
    def test_sessionmanager_creation(self):
        SessionManager()

    def test_sessionmanager_init(self):
        session = SessionManager()
        assert session.current_user is None

    def test_sessionmanager_login(self):
        pass
        # user = User(0, random_bytes())

def watch_random_data(watch_id, bytes_amount=8):
    i = random_bytes(8, bytes_amount)
    watch = Watch(watch_id, i[1], i[2], i[3], i[4], i[5], i[6], i[7])
    return watch

def random_bytes(entries, n):
    i = []
    for x in range(0, entries):
        i.append(random.randbytes(n))
    return i