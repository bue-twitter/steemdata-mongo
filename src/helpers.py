from datetime import datetime

from funcy import flatten
from steem import Steem
from steem.utils import remove_from_dict
from steemdata.helpers import simple_cache, create_cache
from steemdata.markets import Markets

usernames_cache = create_cache()


@simple_cache(usernames_cache, timeout=30 * 60)
def refresh_username_list():
    """
    Only refresh username list every 30 minutes, otherwise return from cache.
    """
    return get_all_usernames()


def extract_usernames_from_op(op):
    """
    Get a list of all STEEM users that were *likely* affected by the op.
    This method only looks into top level keys, and is somewhat obtuse.
    Rather than filtering out irrevenant keys, it might be easier to look for known username containing keys,
    however, we have no guarantees of schema immutability.
    """
    # votes and comments are too noisy (92% of operations)
    if op['type'] in ['vote', 'custom_json', 'curation_reward']:
        return []

    usernames = refresh_username_list()

    irrelevant_fields = ['type', 'block_num', 'permlink', 'timestamp', 'trx_id', 'weight', 'body', 'title',
                         'props', 'work', 'json_metadata', 'json', 'memo']
    op_pruned = remove_from_dict(op, irrelevant_fields)
    matches = [x for x in op_pruned.values() if type(x) == str and x in usernames]

    # remove users with operation like usernames
    return list(set(matches) - {'follow', 'comment', 'vote', 'pow', 'pow2', 'transfer'})


def fetch_comments_flat(root_post=None, comments=list(), all_comments=list()):
    """
    Recursively fetch all the child comments, and return them as a list.

    Usage: all_comments = fetch_comments_flat(Post('@foo/bar'))
    """
    # see if our root post has any comments
    if root_post:
        return fetch_comments_flat(comments=root_post.get_comments())
    if not comments:
        return all_comments

    # recursively scrape children one depth layer at a time
    children = list(flatten([x.get_comments() for x in comments]))
    if not children:
        return all_comments
    return fetch_comments_flat(all_comments=comments + children, comments=children)


def get_all_usernames(last_user=-1, steem=None):
    if not steem:
        steem = Steem()

    usernames = steem.rpc.lookup_accounts(last_user, 1000)
    batch = []
    while len(batch) != 1:
        batch = steem.rpc.lookup_accounts(usernames[-1], 1000)
        usernames += batch[1:]

    return usernames


def get_usernames_batch(last_user=-1, steem=None):
    if not steem:
        steem = Steem()

    return steem.rpc.lookup_accounts(last_user, 1000)


def fetch_price_feed():
    m = Markets()
    return {
        "timestamp": datetime.utcnow(),
        "btc_usd": round(m.btc_usd(), 8),
        "steem_btc": round(m.steem_btc(), 8),
        "sbd_btc": round(m.sbd_btc(), 8),
        "steem_sbd_implied": round(m.steem_sbd_implied(), 6),
        "steem_usd_implied": round(m.steem_usd_implied(), 6),
        "sbd_usd_implied": round(m.sbd_usd_implied(), 6),
    }
