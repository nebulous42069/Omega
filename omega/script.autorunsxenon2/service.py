import re
import json
from default import Autoruns

class Startup(Autoruns):

	def startup(self):
		off_items = json.loads(self.openfile(self.data_file))['items']
		for individual_addon in off_items:
			path_to_addon = self.pathofaddons / individual_addon
			addon_xml_path = path_to_addon / 'addon.xml'
			if not addon_xml_path.exists():
				continue
			xml_content = self.openfile(addon_xml_path)
			on_check = re.search(self.on_pattern, xml_content)
			off_check = re.search(self.off_pattern, xml_content)
			if on_check is not None and off_check is None:
				on_match = re.findall(self.on_pattern, xml_content)[0]
				content = xml_content.replace(on_match, f'<!--{on_match}-->')
				self.savefile(addon_xml_path, content)

if __name__ == '__main__':
	s = Startup()
	if s.data_file.exists():
		s.startup()