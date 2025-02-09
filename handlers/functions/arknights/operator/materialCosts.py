import os

from core.util import log
from core.util.common import text_to_pinyin, remove_punctuation
from core.util.imageCreator import line_height, side_padding
from dataSource import DataSource, Operator

from .initData import InfoInterface, InitData
from .operatorInfo import OperatorInfo

material_images_source = 'resource/images/materials/'
skill_images_source = 'resource/images/skills/'

icon_size = 34


class MaterialCosts:
    def __init__(self, data: DataSource):
        self.data = data
        self.keywords = []

        self.materials = self.data.materials

        self.operator_list = []
        self.operator_map = {}

        self.skill_map = {}
        self.skill_operator = {}

        self.build_dict()

    def build_dict(self):
        log.info('building operator\'s info and skills keywords dict...')

        keywords = ['%s 500 n' % key for key in InitData.voices]

        def append_word(text):
            self.keywords.append(text)
            dict_word = '%s 500 n' % text
            if dict_word not in keywords:
                keywords.append(dict_word)

        for key in InitData.skill_index_list:
            append_word(key)

        for key in InitData.skill_level_list:
            append_word(key)

        for name, item in self.data.operators.items():
            p_name = text_to_pinyin(name)
            e_name = remove_punctuation(item.en_name)

            self.operator_list.append(name)
            self.operator_map[p_name] = name
            self.operator_map[e_name] = name

            append_word(name)
            append_word(p_name)
            append_word(e_name)

            skills = item.skills()[0]

            for skl in skills:
                skl_name = remove_punctuation(skl['skill_name'])
                skl_name_p = text_to_pinyin(skl['skill_name'])

                self.skill_map[skl_name] = skl['skill_name']
                self.skill_map[skl_name_p] = skl['skill_name']

                append_word(skl_name)
                append_word(skl_name_p)

                self.skill_operator[skl['skill_name']] = name

        with open('resource/operators.txt', mode='w', encoding='utf-8') as file:
            file.write('\n'.join(keywords))

    def check_evolve_costs(self, info: InfoInterface):

        if not info.name:
            return '博士，请仔细描述想要查询的信息哦'

        operator: Operator = self.data.operators[info.name]
        evolve_costs = operator.evolve_costs()

        result = []
        for item in evolve_costs:
            if item['evolve_level'] == info.level:
                material = self.materials[item['use_material_id']]
                result.append({
                    'material_name': material['material_name'],
                    'material_icon': material['material_icon'],
                    'use_number': item['use_number']
                })

        return self.__build_evolve_costs(result, info.name, info.level)

    def check_mastery_costs(self, info: InfoInterface):

        check_res = OperatorInfo.check_skill_list(
            self.skill_operator,
            self.data.operators,
            info
        )

        if type(check_res) is str:
            return check_res
        else:
            skill_list, skills_cost, skills_desc = check_res

        result = []

        for skl in skill_list:
            for item in skills_cost[skl['skill_no']]:
                if item['mastery_level'] == info.level:
                    material = self.materials[item['use_material_id']]
                    result.append(
                        {
                            'skill_name': skl['skill_name'],
                            'skill_icon': skl['skill_icon'],
                            'material_name': material['material_name'],
                            'material_icon': material['material_icon'],
                            'use_number': item['use_number']
                        }
                    )

        return self.__build_mastery_costs(result, info.name, info.level)

    @staticmethod
    def __build_evolve_costs(result, name, level):
        evolve = {1: '一', 2: '二'}
        icons = []

        if len(result):
            text = '博士，这是干员%s精英%s需要的材料清单\n\n' % (name, evolve[level])
            images = []
            material_name = []
            for item in result:
                if item['material_name'] not in material_name:
                    text += '%s%s * %s\n\n' % (' ' * 12, item['material_name'], item['use_number'])
                    images.append(material_images_source + item['material_icon'] + '.png')
                    material_name.append(item['material_name'])

            for index, item in enumerate(images):
                if os.path.exists(item):
                    icons.append({
                        'path': item,
                        'size': icon_size,
                        'pos': (5, 26 + index * 34)
                    })
        else:
            text = '博士，暂时没有找到相关的档案哦~'

        return text, icons

    @staticmethod
    def __build_mastery_costs(result, name, level):
        mastery = {1: '一', 2: '二', 3: '三'}
        icons = []

        if len(result):
            text = f'博士，这是干员{name}技能专精{mastery[level]}需要的材料清单\n'
            skills = {}
            skill_images = []
            material_images = []

            for item in result:
                skill_name = item['skill_name']
                if skill_name not in skills:
                    skills[skill_name] = []
                    skill_images.append(skill_images_source + item['skill_icon'] + '.png')
                skills[skill_name].append(item)

            for name in skills:
                text += '\n%s%s\n\n\n' % (' ' * 15, name)
                for item in skills[name]:
                    text += ' -- %s%s * %s\n\n' % (' ' * 15, item['material_name'], item['use_number'])
                    material_images.append(material_images_source + item['material_icon'] + '.png')

            top = side_padding + line_height + int((line_height * 3 - icon_size) / 2)
            content_height = line_height * 10
            for index, item in enumerate(skill_images):
                if os.path.exists(item):
                    icons.append({
                        'path': item,
                        'size': icon_size,
                        'pos': (side_padding, top + content_height * index)
                    })

            top += line_height * 3
            i, n = 0, line_height * 2
            for index, item in enumerate(material_images):
                if index and index % 3 == 0:
                    i += n * 2
                if os.path.exists(item):
                    icons.append({
                        'path': item,
                        'size': icon_size,
                        'pos': (30, top + i)
                    })
                i += n
        else:
            text = f'博士，没有找到干员{name}技能专精{mastery[level]}需要的材料清单'

        return text, icons
