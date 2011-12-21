def join(items, joiner = object()):
	"""Join the items with the specified joiner "in between" each item.
	This works for both sequence types (where the joiner is interspersed
	between items, which are kept in order) and unordered collection types
	such as `set` and `dict`, in which case the union of the joiner and all
	items is taken.

	The `joiner` must be an iterable type, if supplied. Each of the `items`
	must be iterable, and there must be a sane way to join them.

	First, a "result type" is determined. This is the type of the joiner, if
	supplied, or of the first item if the joiner is None. The result will
	normally be of the same type.

	If the result type supplies both 'count' and '__add__' methods (like
	`tuple`, `list` and ascii/Unicode strings do), it is treated as a sequence
	type. Special optimized code is used for the builtin types; otherwise the
	__add__ method of the type is called repeatedly to concatenate the items.
	(The check for a 'count' method is intended to prevent `join` from being
	used with numeric types, where it makes no sense). Note that if the `items`
	contain a mixture of lists and tuples, which are normally incompatible,
	`join` will still work, creating a list or tuple of items according to the
	type of the first item.

	Otherwise, if the result type provides an 'update' method (like `set` and
	`dict`), it is treated as an unordered collection. If a 'union' method is
	also provided, it will be used to add all the items together at once;
	otherwise, each will be added one at a time with 'update'. Note that the
	result will be empty (i.e. not contain any elements from the `joiner`) if
	there are no `items`, just as it would be with the sequence types.

	If that fails, an iterator is formed for each element and all the iterators
	are chained together (interspersed with iterators over the `joiner`).

	In all cases, the supplied `joiner` object will not be modified by `join`.
	If `items` is a generator or iterator, it will of course be modified, but
	the underlying items should be unaffected.

	Whatever the result type is, it is assumed that calling its constructor
	with no arguments produces an "empty" instance that has no effect when
	"appended" to another instance."""

	if joiner is join.func_defaults[0]:
		if not items: raise TypeError, "No joiner and nothing to join"
	else:
		iter(joiner) # ensure joiner is iterable, let TypeError propagate
		if not items: return type(joiner)()

	# If we get here, joiner is OK and there is at least one item.

	# Force evaluation of generator if 'items' is a generator. Testing shows
	# it's comparable in speed to explicitly calling `list` or `tuple`.
	# Also allows simple access to the first element.
	return join_helper(joiner, *items)


def join_helper(joiner, first, *items):
	no_joiner = joiner is join.func_defaults[0]
	prototype = first if no_joiner else joiner
	result_type = type(prototype)

	if hasattr(prototype, 'count') and hasattr(prototype, '__add__'):
		# Sequence type. Check for library types first.
		# Types derived from tuple and list are promoted to the base type
		# if the result can't be converted to the derived type.
		# This handles `collections.namedtuple`.
		if isinstance(prototype, (tuple, list)):
			# join_lists receives a copy of the first element, which it may modify.
			result = join_lists([] if no_joiner else joiner, list(first), items)
			try:
				# Convert the result.
				return result_type(result)
			except:
				if isinstance(prototype, tuple): return tuple(result)
				# The result is already a list, but this ensures that the storage
				# space is 'trimmed'.
				return list(result)
		elif isinstance(prototype, basestring):
			if no_joiner: joiner = ''
			return first + joiner + joiner.join(items)
		else:
			return reduce(
				result_type.__add__,
				(item if no_joiner else joiner + item for item in items),
				first
			)
	elif hasattr(result_type, 'update'):
		return (
			result_type().union(joiner, first, *items)
			if hasattr(result_type, 'union')
			else join_by_update(result_type(), joiner, first, *items)
		)
	else:
		# Chain iterators.
		# You are not expected to understand this. Unless you're Dutch.
		from itertools import chain, izip, tee
		to_chain = [iter(x) for x in items]
		return chain(iter(first), *(
			to_chain
			if no_joiner else chain(
				*izip(
					tee(iter(joiner), len(to_chain)), to_chain
				)
			)
		))


# Pulling this into a separate function makes it easier to put 'first'
# back into the list. TODO check if this is inefficient.
def join_by_update(result, *items):
	for item in items: result.update(item)
	return result


def join_lists(joiner, result, items):
	# Alternate appending joiner and an item to result.
	# First decide whether to count and presize.
	li = len(items)
	lj = len(joiner)
	if li > 100: # point at which it becomes worthwhile, approximately.
		# This was determined by tests with `timeit` where the individual lists
		# were of the same length as the list of lists (which seems like a
		# reasonable estimate on average). Getting more accurate than this
		# heuristic would pretty much require just doing the work anyway :/
		# Anyway, in this case, we resize the list first by appending a bunch of
		# None elements, and then splice in the new contents.
		count = sum(len(item) for item in items) + li * lj
		index = len(result)
		result.extend([None] * count)
		for item in items:
			result[index:index + lj] = joiner
			result[index + lj:index + lj + len(item)] = item
			index += lj + len(item)
	else:
		# For smaller lists, we just use list.extend() and let the automatic
		# list resizing do its thing. This avoids the need to set a bunch of
		# useless references to None and a bunch of arithmetic, but incurs
		# multiple allocations (though O(lg(N)) in the final size).
		for item in items:
			result.extend(joiner)
			result.extend(item)
	return result
