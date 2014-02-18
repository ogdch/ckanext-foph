# coding: utf-8

import xlrd
import os
from boto.s3.connection import S3Connection
from boto.s3.key import Key
from uuid import NAMESPACE_OID, uuid4, uuid5
import tempfile

from ckan import model
from ckan.model import Session, Package
from ckan.logic import get_action, action
from ckan.lib.helpers import json
from ckanext.harvest.harvesters.base import munge_tag
from ckan.lib.munge import munge_title_to_name

from ckanext.harvest.model import HarvestObject
from ckanext.harvest.harvesters import HarvesterBase

from pylons import config

import logging
log = logging.getLogger(__name__)


class FOPHHarvester(HarvesterBase):

    '''
    The harvester for the FOPH
    '''

    BUCKET_NAME = config.get('ckanext.foph.s3_bucket')
    METADATA_FILE_NAME = u'OGD_Metadaten_BAG.xlsx'
    DEPARTMENT_BASE = u'ch.bag/'
    FILES_BASE_URL = 'http://' + BUCKET_NAME + '.s3.amazonaws.com'

    # Define the keys in the CKAN .ini file
    AWS_ACCESS_KEY = config.get('ckanext.foph.s3_key')
    AWS_SECRET_KEY = config.get('ckanext.foph.s3_token')

    FOLDERS = {
        'pri': u'Praemien/',
        'kzp': u'Spitalstatistikdateien/kzp/',
        'qip': u'Spitalstatistikdateien/qip/'
    }

    ORGANIZATION = {
        'de': {
            'name': u'Bundesamt für Gesundheit BAG',
            'description':
            u'Das Bundesamt für Gesundheit (BAG) ist Teil des Eidgenössischen '
            + u'Departements des Innern. Es ist - zusammen mit den Kantonen '
            + u'- verantwortlich für die Gesundheit der Schweizer '
            + u'Bevölkerung und für die Entwicklung der nationalen '
            + u'Gesundheitspolitik. Zudem vertritt das BAG als nationale '
            + u'Behörde die Schweiz in Gesundheitsbelangen in '
            + u'internationalen Organisationen und gegenüber anderen '
            + u'Staaten.',
            'website': u'http://www.bar.admin.ch/'
        },
        'fr': {
            'name': u'Office fédéral de la santé publique OFSP',
            'description':
            u"L'Office fédéral de la santé publique (OFSP) fait partie du "
            + u"Département fédéral de l'intérieur. De concert avec les "
            + u"cantons, il assume la responsabilité des domaines touchant "
            + u"à la santé publique ainsi que la mise en œuvre de la "
            + u"politique sanitaire. Autorité à vocation nationale, il "
            + u"représente les intérêts sanitaires de la Suisse dans les "
            + u"organisations internationales et auprès d'autres Etats."
        },
        'it': {
            'name': u'Ufficio federale della sanità pubblica UFSP',
            'description':
            u"L'Ufficio federale della sanità pubblica (UFSP) è incorporato "
            + u"nel Dipartimento federale dell'interno. Unitamente ai "
            + u"Cantoni, è responsabile della salute della popolazione "
            + u"svizzera e dello sviluppo della politica nazionale in "
            + u"materia di salute. In qualità di autorità nazionale "
            + u"rappresenta inoltre gli interessi della Svizzera in "
            + u"materia di sanità in seno a organizzazioni internazionali "
            + u"e nei rapporti con altri Stati."
        },
        'en': {
            'name': u'Federal Office of Public Health FOPH',
            'description':
            u"The Federal Office of Public Health (FOPH) is part of the "
            + u"Federal Department of Home Affairs. Along with the cantons "
            + u"it is responsible for public health in Switzerland and for "
            + u"developing national health policy. As the national health "
            + u"authority, the FOPH also represents Switzerland's "
            + u"interests in the field of health in international "
            + u"organisations and with respect to other countries."
        }
    }
    LANG_CODES = ['de', 'fr', 'it', 'en']

    GROUPS = {
        u'de': [u'Gesundheit'],
        u'fr': [u'Santé'],
        u'it': [u'Salute'],
        u'en': [u'Health']
    }

    config = {
        'user': u'harvest'
    }

    def _get_s3_bucket(self):
        '''
        Create an S3 connection to the department bucket
        '''
        conn = S3Connection(self.AWS_ACCESS_KEY, self.AWS_SECRET_KEY)
        bucket = conn.get_bucket(self.BUCKET_NAME)
        return bucket

    def _fetch_metadata_file(self):
        '''
        Fetching the Excel metadata file for the FOPH from the S3 Bucket
        and save on disk
        '''
        temp_dir = tempfile.mkdtemp()
        try:
            metadata_file = Key(self._get_s3_bucket())
            metadata_file.key = self.METADATA_FILE_NAME
            metadata_file_path = os.path.join(
                temp_dir,
                self.METADATA_FILE_NAME)
            log.debug('Saving metadata file to %s' % metadata_file_path)
            metadata_file.get_contents_to_filename(metadata_file_path)
            return metadata_file_path
        except Exception as e:
            log.exception(e)
            raise

    def _guess_format(self, file_name):
        '''
        Return the format for a given full filename
        '''
        _, file_extension = os.path.splitext(file_name.lower())
        return file_extension[1:]

    def _generate_resources_dict_array(self, dataset_id):
        '''

        '''
        try:
            resources = []
            prefix = self.DEPARTMENT_BASE + self.FOLDERS[dataset_id[:3]]
            if dataset_id != u'prim':
                prefix = prefix + u'20' + dataset_id[3:] + u'/'
            bucket_list = self._get_s3_bucket().list(prefix=prefix)
            for file in bucket_list:
                if file.key != prefix:
                    resources.append({
                        'url': self.FILES_BASE_URL + '/' + file.key,
                        'name': file.key.replace(prefix, u''),
                        'format': self._guess_format(file.key),
                        'size': self._get_s3_bucket().lookup(file.key).size
                    })
            return resources
        except Exception as e:
            log.exception(e)
            raise

    def _get_col_dict_array(self, lang_index, file_path):
        '''
        Returns a list of dicts, one for each dataset (= each sheet in
        the metadata file).
        '''
        try:
            metadata_workbook = xlrd.open_workbook(file_path)
            cols = []

            for sheet_name in metadata_workbook.sheet_names():
                worksheet = metadata_workbook.sheet_by_name(sheet_name)
                attributes = worksheet.col_values(0, 2, 14)
                # Lang_index + 1 is used to get the column number, because col
                # 0 contains the attributes
                cols.append(
                    dict(zip(attributes, worksheet.col_values(
                        lang_index + 1,
                        2,
                        14
                    ))))
            return cols

        except Exception as e:
            log.exception(e)
            raise

    def _generate_term_translations(self, lang_index, file_path):
        '''
        '''
        try:
            translations = []

            de_cols = self._get_col_dict_array(0, file_path)
            other_cols = self._get_col_dict_array(lang_index, file_path)

            log.debug(de_cols)
            log.debug(other_cols)

            keys = ['title', 'notes', 'author', 'maintainer', 'license_id']

            for col_idx in range(len(de_cols)):
                for key in keys:
                    translations.append({
                        'lang_code': self.LANG_CODES[lang_index],
                        'term': de_cols[col_idx][key],
                        'term_translation': other_cols[col_idx][key]
                    })

                de_tags = de_cols[col_idx]['tags'].split(u', ')
                other_tags = other_cols[col_idx]['tags'].split(u', ')

                if len(de_tags) == len(other_tags):
                    for tag_idx in range(len(de_tags)):
                        translations.append({
                            'lang_code': self.LANG_CODES[lang_index],
                            'term': munge_tag(de_tags[tag_idx]),
                            'term_translation': munge_tag(other_tags[tag_idx])
                        })

            for lang, org in self.ORGANIZATION.items():
                if lang != 'de':
                    for field in ['name', 'description']:
                        translations.append({
                            'lang_code': lang,
                            'term': self.ORGANIZATION['de'][field],
                            'term_translation': org[field]
                        })

            for lang, groups in self.GROUPS.iteritems():
                if lang != u'de':
                    for idx, group in enumerate(self.GROUPS[lang]):
                        translations.append({
                            'lang_code': lang,
                            'term': self.GROUPS[u'de'][idx],
                            'term_translation': group
                        })

            return translations

        except Exception as e:
            log.exception(e)
            raise

    def _create_uuid(self, name=None):
        '''
        Create a new SHA-1 uuid for a given name or a random id
        '''
        if name:
            new_uuid = uuid5(NAMESPACE_OID, str(name))
        else:
            new_uuid = uuid4()

        return unicode(new_uuid)

    def _gen_new_name(self, title, current_id=None):
        '''
        Creates a URL friendly name from a title

        If the name already exists, it will add some random characters
        at the end
        '''

        name = munge_title_to_name(title).replace('_', '-')
        while '--' in name:
            name = name.replace('--', '-')
        pkg_obj = Session.query(Package).filter(Package.name == name).first()
        if pkg_obj and pkg_obj.id != current_id:
            return name + str(uuid4())[:5]
        else:
            return name

    def info(self):
        return {
            'name': 'foph',
            'title': 'FOPH',
            'description': 'Harvests the FOPH data',
            'form_config_interface': 'Text'
        }

    def _find_or_create_groups(self, context):
        group_name = self.GROUPS['de'][0]
        data_dict = {
            'id': group_name,
            'name': munge_title_to_name(group_name),
            'title': group_name
        }
        try:
            group = get_action('group_show')(context, data_dict)
        except:
            group = get_action('group_create')(context, data_dict)
            log.info('created the group ' + group['id'])
        group_ids = []
        group_ids.append(group['id'])
        return group_ids

    def gather_stage(self, harvest_job):
        log.debug('In FOPHHarvester gather_stage')
        try:
            file_path = self._fetch_metadata_file()
            ids = []

            de_cols = self._get_col_dict_array(0, file_path)
            for col in de_cols:
                # Construct the metadata dict for the dataset on CKAN
                metadata = {
                    'datasetID': col[u'id'],
                    'title': col[u'title'],
                    'url': col[u'url'],
                    'notes': col[u'notes'],
                    'author': col[u'author'],
                    'author_email': col[u'author_email'],
                    'maintainer': col[u'maintainer'],
                    'maintainer_email': col[u'maintainer_email'],
                    'license_id': col[u'license_id'].lower(),
                    'version': col[u'version'],
                    'translations': [],
                    'tags': col[u'tags'].split(u', ')
                }

                metadata['resources'] = self._generate_resources_dict_array(
                    col[u'id'])
                metadata['resources'][0]['version'] = col[u'version']
                log.debug(metadata['resources'])

                # Adding term translations
                metadata['translations'].extend(
                    self._generate_term_translations(1, file_path))  # fr
                metadata['translations'].extend(
                    self._generate_term_translations(2, file_path))  # it
                metadata['translations'].extend(
                    self._generate_term_translations(3, file_path))  # en

                log.debug(metadata['translations'])

                obj = HarvestObject(
                    guid=self._create_uuid(col[u'id']),
                    job=harvest_job,
                    content=json.dumps(metadata)
                )
                obj.save()
                log.debug('adding ' + col[u'id'] + ' to the queue')
                ids.append(obj.id)

                log.debug(de_cols)
        except Exception:
            return False
        return ids

    def fetch_stage(self, harvest_object):
        log.debug('In FOPHHarvester fetch_stage')

        # Get the URL
        datasetID = json.loads(harvest_object.content)['datasetID']
        log.debug(harvest_object.content)

        # Get contents
        try:
            harvest_object.save()
            log.debug('successfully processed ' + datasetID)
            return True
        except Exception as e:
            log.exception(e)
            raise

    def import_stage(self, harvest_object):
        log.debug('In FOPHHarvester import_stage')

        if not harvest_object:
            log.error('No harvest object received')
            return False

        try:
            package_dict = json.loads(harvest_object.content)
            package_dict['id'] = harvest_object.guid
            package_dict['name'] = self._gen_new_name(
                package_dict[u'title'],
                package_dict['id'])

            user = model.User.get(self.config['user'])
            context = {
                'model': model,
                'session': Session,
                'user': self.config['user']
            }

            # Find or create group the dataset should get assigned to
            package_dict['groups'] = self._find_or_create_groups(context)

            # Find or create the organization the dataset should get assigned
            # to.
            data_dict = {
                'permission': 'edit_group',
                'id': munge_title_to_name(self.ORGANIZATION['de']['name']),
                'name': munge_title_to_name(self.ORGANIZATION['de']['name']),
                'title': self.ORGANIZATION['de']['name'],
                'description': self.ORGANIZATION['de']['description'],
                'extras': [
                    {
                        'key': 'website',
                        'value': self.ORGANIZATION['de']['website']
                    }
                ]
            }
            try:
                package_dict['owner_org'] = get_action(
                    'organization_show')(context,
                                         data_dict)['id']
            except:
                organization = get_action(
                    'organization_create')(
                    context,
                    data_dict)
                package_dict['owner_org'] = organization['id']

            # Save additional metadata in extras
            extras = []
            if 'license_url' in package_dict:
                extras.append(('license_url', package_dict['license_url']))
            package_dict['extras'] = extras
            log.debug('Extras %s' % extras)

            # Insert or update the package
            package = model.Package.get(package_dict['id'])
            model.PackageRole(
                package=package,
                user=user,
                role=model.Role.ADMIN
            )

            self._create_or_update_package(
                package_dict,
                harvest_object
            )

            # Add the translations to the term_translations table
            for translation in package_dict['translations']:
                action.update.term_translation_update(context, translation)
            Session.commit()

        except Exception as e:
            log.exception(e)
            raise

        return True
