import math
import random
import numpy as np

import pygame
import os
import config

from itertools import permutations
# radi brze od priorityQ jer nije thread safe i nema trosenja vremena na taj deo, a ovde nije ni potreban
import heapq


class BaseSprite(pygame.sprite.Sprite):
    images = dict()

    def __init__(self, x, y, file_name, transparent_color=None, wid=config.SPRITE_SIZE, hei=config.SPRITE_SIZE):
        pygame.sprite.Sprite.__init__(self)
        if file_name in BaseSprite.images:
            self.image = BaseSprite.images[file_name]
        else:
            self.image = pygame.image.load(os.path.join(config.IMG_FOLDER, file_name)).convert()
            self.image = pygame.transform.scale(self.image, (wid, hei))
            BaseSprite.images[file_name] = self.image
        # making the image transparent (if needed)
        if transparent_color:
            self.image.set_colorkey(transparent_color)
        self.rect = self.image.get_rect()
        self.rect.topleft = (x, y)


class Surface(BaseSprite):
    def __init__(self):
        super(Surface, self).__init__(0, 0, 'terrain.png', None, config.WIDTH, config.HEIGHT)


class Coin(BaseSprite):
    def __init__(self, x, y, ident):
        self.ident = ident
        super(Coin, self).__init__(x, y, 'coin.png', config.DARK_GREEN)

    def get_ident(self):
        return self.ident

    def position(self):
        return self.rect.x, self.rect.y

    def draw(self, screen):
        text = config.COIN_FONT.render(f'{self.ident}', True, config.BLACK)
        text_rect = text.get_rect(center=self.rect.center)
        screen.blit(text, text_rect)


class CollectedCoin(BaseSprite):
    def __init__(self, coin):
        self.ident = coin.ident
        super(CollectedCoin, self).__init__(coin.rect.x, coin.rect.y, 'collected_coin.png', config.DARK_GREEN)

    def draw(self, screen):
        text = config.COIN_FONT.render(f'{self.ident}', True, config.RED)
        text_rect = text.get_rect(center=self.rect.center)
        screen.blit(text, text_rect)


class Agent(BaseSprite):
    def __init__(self, x, y, file_name):
        super(Agent, self).__init__(x, y, file_name, config.DARK_GREEN)
        self.x = self.rect.x
        self.y = self.rect.y
        self.step = None
        self.travelling = False
        self.destinationX = 0
        self.destinationY = 0

    def set_destination(self, x, y):
        self.destinationX = x
        self.destinationY = y
        self.step = [self.destinationX - self.x, self.destinationY - self.y]
        magnitude = math.sqrt(self.step[0] ** 2 + self.step[1] ** 2)
        self.step[0] /= magnitude
        self.step[1] /= magnitude
        self.step[0] *= config.TRAVEL_SPEED
        self.step[1] *= config.TRAVEL_SPEED
        self.travelling = True

    def move_one_step(self):
        if not self.travelling:
            return
        self.x += self.step[0]
        self.y += self.step[1]
        self.rect.x = self.x
        self.rect.y = self.y
        if abs(self.x - self.destinationX) < abs(self.step[0]) and abs(self.y - self.destinationY) < abs(self.step[1]):
            self.rect.x = self.destinationX
            self.rect.y = self.destinationY
            self.x = self.destinationX
            self.y = self.destinationY
            self.travelling = False

    def is_travelling(self):
        return self.travelling

    def place_to(self, position):
        self.x = self.destinationX = self.rect.x = position[0]
        self.y = self.destinationX = self.rect.y = position[1]

    # coin_distance - cost matrix
    # return value - list of coin identifiers (containing 0 as first and last element, as well)
    def get_agent_path(self, coin_distance):
        pass


class ExampleAgent(Agent):
    def __init__(self, x, y, file_name):
        super().__init__(x, y, file_name)

    def get_agent_path(self, coin_distance):
        path = [i for i in range(1, len(coin_distance))]
        random.shuffle(path)
        return [0] + path + [0]


class Aki(Agent):
    def __init__(self, x, y, file_name):
        super().__init__(x, y, file_name)

    def get_agent_path(self, coin_distance):
        num_of_coins = len(coin_distance)
        path = [0]
        curr_pos = 0

        for i in range(num_of_coins):
            curr_values = coin_distance[curr_pos]
            curr_tuple = []

            for index, value in enumerate(curr_values):
                curr_tuple.append((index, value))

            curr_tuple.sort(key=lambda tup: (tup[1], tup[0]))

            j = 0
            while True:
                tmp_pos = curr_tuple[j][0]
                if tmp_pos not in path:
                    curr_pos = tmp_pos
                    path.append(curr_pos)
                    break
                j += 1

                if j == num_of_coins:
                    break

        return path + [0]


def all_path_permutations(path):
    reversed_elements = set()
    for i in permutations(path):
        if i not in reversed_elements:
            reversed_i = tuple(reversed(i))
            reversed_elements.add(reversed_i)
            yield (i)


class Jocke(Agent):
    def __init__(self, x, y, file_name):
        super().__init__(x, y, file_name)

    def get_agent_path(self, coin_distance):
        num_of_coins = len(coin_distance)
        all_paths = list(all_path_permutations(list(range(1, num_of_coins))))
        min_value = math.inf
        min_path = []

        for elem in all_paths:
            start_pos = 0
            curr_value = 0
            for i in elem:
                curr_value += coin_distance[start_pos][i]
                start_pos = i
            curr_value += coin_distance[start_pos][0]
            if curr_value < min_value:
                min_value = curr_value
                min_path = elem

        path = np.asarray(min_path)
        path = np.concatenate(([0], path[:], [0]))
        return path


class Uki(Agent):
    def __init__(self, x, y, file_name):
        super().__init__(x, y, file_name)

    # branch and bound
    # imamo sortiranu listu po : crit1(cena), crit2(brZlatnika), crit3(manjaVrOznaka)

    # TODO: ne ubacivati simetricne puteve
    def get_agent_path(self, coin_distance):
        num_of_nodes = len(coin_distance)
        sorted_list = []

        heapq.heapify(sorted_list)

        i = 1

        # cost, brZlatnika, destinacija, lista(od 0 do te destinacije)
        while True:
            heapq.heappush(sorted_list, (coin_distance[0][i], 0, i, [0, i]))
            i += 1
            if i == num_of_nodes:
                break

        # po broju sakupljenih izmedju pocetka i kraja(bez pocetne 0), po krajnjoj destinaciji puta

        curr_position = heapq.heappop(sorted_list)

        while True:
            if len(curr_position[3]) == (num_of_nodes + 1):
                path = curr_position[3]
                break

            for i in range(1, num_of_nodes):
                if i not in curr_position[3]:
                    heapq.heappush(sorted_list, (curr_position[0] + coin_distance[curr_position[2]][i],
                                                 (len(curr_position[3]) - 1) * -1, i, curr_position[3] + [i]))

            if len(curr_position[3]) == num_of_nodes:  # fali samo 0
                heapq.heappush(sorted_list, (curr_position[0] + coin_distance[curr_position[2]][0],
                                             (len(curr_position[3]) - 1) * -1, 0, curr_position[3] + [0]))

            curr_position = heapq.heappop(sorted_list)

        return path


def kruskal_mst(without, size, paths, history_dict):
    vertices_num = 0
    mst_sum = 0

    # na pocetku svako je posebno stablo
    parent = [i for i in range(0, size)]

    while True:
        if vertices_num == size - 1 - len(without):
            break
        curr_node = heapq.heappop(paths)
        if curr_node[1][0] in without or curr_node[1][1] in without:
            continue
        if parent[curr_node[1][0]] == parent[curr_node[1][1]]:
            continue
        else:
            mst_sum += curr_node[0]

            for i in range(size):
                if parent[i] == curr_node[1][1]:
                    parent[i] = curr_node[1][0]

            vertices_num += 1

    # sortitamo tuple da ne bi bilo slucaja kada pamtimo 1,2,3 i 3,2,1 u dict-u
    key = tuple(sorted(without))
    history_dict[key] = mst_sum

    return mst_sum


class Micko(Agent):
    def __init__(self, x, y, file_name):
        super().__init__(x, y, file_name)

    def get_agent_path(self, coin_distance):
        paths = []
        i = 1
        j = 0
        num_of_nodes = len(coin_distance)
        mst_cost_dict = {}
        heapq.heapify(paths)

        # generisemo sve grane na pocetku
        while j < num_of_nodes:
            k = i
            while k < num_of_nodes:
                heapq.heappush(paths, (coin_distance[j][k], [j, k]))
                k += 1
            j += 1
            i += 1

        sorted_list = []

        heapq.heapify(sorted_list)

        i = 1

        # list(paths) salje kopiju
        mst_cost = kruskal_mst([], num_of_nodes, list(paths), mst_cost_dict)
        while True:
            heapq.heappush(sorted_list, (coin_distance[0][i] + mst_cost, 0, i, [0, i]))
            i += 1
            if i == num_of_nodes:
                break

        curr_position = heapq.heappop(sorted_list)

        while True:
            if len(curr_position[3]) == (num_of_nodes + 1):
                path = curr_position[3]
                break

            size = len(curr_position[3])

            # jer nema smisla da trazimo mst sa samo jednim cvorom ili kada imamo samo pocetak i kraj

            if 2 <= size < num_of_nodes:
                without = tuple(sorted(curr_position[3][1:size]))
                if without not in mst_cost_dict:
                    mst_cost = kruskal_mst(without, num_of_nodes, list(paths), mst_cost_dict)
                else:
                    mst_cost = mst_cost_dict[without]

            for i in range(1, num_of_nodes):
                if i not in curr_position[3]:
                    heapq.heappush(sorted_list, (curr_position[0] + coin_distance[curr_position[2]][i] + mst_cost,
                                                 (size - 1) * -1, i, curr_position[3] + [i]))

            if size == num_of_nodes:  # fali samo 0, ovde je mst_cost = 0, jer su na parcijalnoj putanji svi osim 0
                heapq.heappush(sorted_list, (curr_position[0] + coin_distance[curr_position[2]][0],
                                             (size - 1) * -1, 0, curr_position[3] + [0]))

            curr_position = heapq.heappop(sorted_list)

        return path
