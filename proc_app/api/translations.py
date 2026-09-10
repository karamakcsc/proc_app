class CaseInsensitiveTranslations(dict):
	"""A translation dict whose .get() falls back to a case-insensitive match.

	Needed because templates use the same t.get(key, fallback) call for two
	different things: static UI copy, where the key is a hand-written
	snake_case string the template author chose (e.g. t.get("submit_request",
	"Submit Request")), and dynamic values straight from Frappe -- workflow
	action names ("Approve"), workflow states ("Pending Requesting-Dept
	Approval") -- looked up via t.get(value, value), where the "key" IS the
	real value and arrives in whatever case Frappe's own naming convention
	uses (Title Case for Workflow Action Master / Workflow State names).

	An exact match is always tried first, so every existing snake_case call
	site (which already only ever hits its own exact, already-lowercase key)
	behaves identically to a plain dict -- this class only changes behaviour
	for a lookup whose exact key is missing, which was already a silent
	fallback-to-English miss before this existed. Shared by supplier_portal
	and proc_portal (both call get_translations(), which wraps its merged
	shared+own dict in this class) so the two apps' identically-named
	mechanism doesn't drift into two different casing behaviours.
	"""

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._lower_map = {}
		for k, v in self.items():
			self._lower_map.setdefault(k.lower(), v)

	def get(self, key, default=None):
		if super().__contains__(key):
			return super().__getitem__(key)
		if isinstance(key, str):
			hit = self._lower_map.get(key.lower())
			if hit is not None:
				return hit
		return default
