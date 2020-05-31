"""Helper for finding and listing contacts from the contacts.yml database.
Prints name, institution, and email (if applicable) of the contact.
"""
import datetime 
import dateutil
import dateutil.parser as date_parser
from dateutil.relativedelta import relativedelta
import sys


from regolith.helpers.basehelper import SoutHelperBase
from regolith.fsclient import _id_key
from regolith.tools import (
    all_docs_from_collection,
    get_pi_id,
    fuzzy_retrieval,
)

TARGET_COLL = "contacts"
HELPER_TARGET = "l_contacts"

def subparser(subpi):
    subpi.add_argument("-n", "--name", help='finds contacts based off a list of names or name fragments', nargs = '+')
    subpi.add_argument("-i", "--inst", help='finds contacts based off an institution or an institution fragment')
    subpi.add_argument("-d", "--date", help='finds contacts based off a date in ISO format (YYYY-MM-DD) with a default range of 4 months centered around the date (d +/- 2 month)')
    subpi.add_argument("-r", "--range", help='optional argument that sets range (in months) centered around date d (d +/- r/2)')
    subpi.add_argument("-no", "--notes", help='finds contacts based off notes or miscellaneous information about the contact', nargs = '+')
    return subpi

def is_current(thing, now=None):
    """
    given a thing with dates, returns true if the thing is current
    looks for begin_ and end_ daty things (date, year, month, day), or just
    the daty things themselves. e.g., begin_date, end_month, month, and so on.
    Parameters
    ----------
    thing: dict
      the thing that we want to know whether or not it is current
    now: datetime.date object
      a date for now.  If it is None it uses the current date.  Default is None
    Returns
    -------
    True if the thing is current and false otherwise
    """
    if not now:
        now = datetime.date.today()
    dates = thing
    current = False
    try:
        if dates.get("begin_date") <= now <= dates.get("end_date", datetime.date(5000, 12, 31)):
            current = True
    except:
        raise RuntimeError(f"Cannot find begin_date in document:\n {thing}")
    return current

class ContactsListerHelper(SoutHelperBase):
    """Helper for listing upcoming (and past) projectum milestones.

       Projecta are small bite-sized project quanta that typically will result in
       one manuscript.
    """
    # btype must be the same as helper target in helper.py
    btype = HELPER_TARGET
    needed_dbs = [f'{TARGET_COLL}']

    def construct_global_ctx(self):
        """Constructs the global context"""
        super().construct_global_ctx()
        gtx = self.gtx
        rc = self.rc
        if "groups" in self.needed_dbs:
            rc.pi_id = get_pi_id(rc)
        rc.coll = f"{TARGET_COLL}"
        try:
            if not rc.database:
                rc.database = rc.databases[0]["name"]
        except:
            pass
        colls = [
            sorted(
                all_docs_from_collection(rc.client, collname), key=_id_key
            )
            for collname in self.needed_dbs
        ]
        for db, coll in zip(self.needed_dbs, colls):
            gtx[db] = coll
        gtx["all_docs_from_collection"] = all_docs_from_collection
        gtx["float"] = float
        gtx["str"] = str
        gtx["zip"] = zip


    def sout(self):
        rc = self.rc
        contacts = []
        if rc.date:
            temp_dat = date_parser.parse(rc.date).date()
        for contact in self.gtx["contacts"]:
            if rc.name:
                list_add = False
                for nam in rc.name:
                     if nam.casefold() in contact.get('name').casefold():
                        contacts.append(contact)
                        list_add = True
                if list_add:
                    continue
            if rc.inst and (rc.inst.casefold() in contact.get('institution').casefold()):
                contacts.append(contact)
                continue
            if rc.date:
                if rc.range:
                    temp_dict = {"begin_date":temp_dat - dateutil.relativedelta.relativedelta(months=int(rc.range)), "end_date":temp_dat + dateutil.relativedelta.relativedelta(months=int(rc.range))} 
                else:
                    temp_dict = {"begin_date":temp_dat - dateutil.relativedelta.relativedelta(months=2), "end_date":temp_dat + dateutil.relativedelta.relativedelta(months=2)}                
                if is_current(temp_dict, now=temp_dat):
                    contacts.append(contact)
                    continue
            if rc.notes:
                list_add = False
                for note in rc.notes:
                    if isinstance(contact.get('notes'),str):
                        if note.casefold() in contact.get('notes').casefold():
                            contacts.append(contact)
                            list_add = True
                    elif isinstance(contact.get('notes'),list):
                        for no in contact.get('notes'):
                             if note.casefold() in no.casefold():
                                 contacts.append(contact)
                                 list_add = True
        for con in contacts:
            if con.get('email'):
                print(f"name: {con.get('name')}, institution: {con.get('institution')}, email: {con.get('email')}")
            else:
                print(f"name: {con.get('name')}, institution: {con.get('institution')}")                
        return

