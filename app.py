import streamlit as st
import numpy as np
import zipfile
import tempfile
import pprint
import os
import csv
import base64
from examples.HanLab_calculate_ODNP import hanlab_calculate_odnp
from dnpLab.dnpHydration import HydrationParameter

print = pprint.pprint

# TEMPDIR = '/tmp/odnplab/'
TEMPDIR = None
CNSI_EMX_LINK = 'https://www.mrl.ucsb.edu/spectroscopy-facility/instruments/7-bruker-emxplus-epr-spectrometer'
DEMO_DATA_LINK = 'https://github.com/ylin00/odnplab/raw/master/20190821_TW_4OH-TEMPO_500uM_.zip'
ISSUE_COMPLAINT_LINK = 'https://github.com/ylin00/odnplab/issues'


def get_table_download_link(temp_file_path, filename='results'):
    """Generates a link allowing a temp_file_path to be downloaded
    
    Args:
        temp_file_path(str): A string to write to a txt file and download.
        filename(str): the txt file name to generate.

    """
    b64 = base64.b64encode(temp_file_path.encode()).decode()  # some strings <-> bytes conversions necessary here
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}.txt">Download Results</a>'
    return href


def set_ppar(ppar:dict):
    """Prompt for users to choose parameters

    Returns: dict

    """
    # Processing parameter
    st.sidebar.markdown("**Enhancement integration**")
    ppar['eiw'] = st.sidebar.slider("Width", min_value=10, max_value=500, value=20, step=10, key='eiw')
    st.sidebar.markdown("**T1 integration**")
    if not st.sidebar.checkbox("Same as Enhancement", value=True):
        ppar['tiw'] = st.sidebar.slider("Width", min_value=10, max_value=500, value=20, step=10, key='tiw')
    else:
        ppar['tiw'] = ppar['eiw']

    return ppar


def set_hpar(hpar:HydrationParameter):
    """Prompt for users to choose parameters

    Returns: tuple(ProcParameter, HydrationParameter)

    """
    # Processing parameter
    st.sidebar.markdown('**Hydration**')
    hpar.spin_C = st.sidebar.number_input("Spin label concentration (uM)", value=500.0, step=1.0, key='spin_C')
    hpar.field = st.sidebar.number_input("Field (mT)", value=hpar.field, step=1.0, key='field')
    hpar.smax_model = st.sidebar.radio('The spin is ', options=['tethered', 'free'], key='smax_model')
    hpar.t1_interp_method = st.sidebar.radio('T1 interpolation method', options=['linear', 'second_order'], index=0, key='t1_interp_method')

    # if st.sidebar.button('More'):
    #     st.write("No more")

    return hpar


def run(uploaded_file, ppar:dict, hpar:HydrationParameter):
    """

    Args:
        uploaded_file: zip file object

    Returns: tuple(dict, str)
        mydict: dictionary of results
        expname: name of the experiment

    """
    # print(f"You just upload this file -> {uploaded_file}")
    # print(f"But I am in a demo mode and not going to run it actually")

    with tempfile.TemporaryDirectory(dir=TEMPDIR) as tmpdir:

        # upzip to tmpdir
        with zipfile.ZipFile(uploaded_file, "r") as zip_ref:
            zip_ref.extractall(tmpdir)
            # Select the first folder ended with '/1/', no matter how deep
            expname = sorted([x for x in zip_ref.namelist() if x[-3:] == '/1/' and 'pdata' not in x])
            if expname is None or len(expname) == 0:
                st.markdown(f"""
                ## Error
                I could not find a folder with experiment number 1.
                
                Could you double check if you have `my_odnp_exp/1/`?
                
                If problems are still there, please report the issue below.
                 """)
                return {}, ''
            else:
                expname = expname[0][0:-2]

        # Process CNSI ODNP and return a str of results
        path = os.path.join(tmpdir, expname)  # path to CNSI data folder

        hresults = hanlab_calculate_odnp(path, ppar, verbose=False)

        # Create dictionary of results
        mydict = {k:v for k, v in hresults.__dict__.items()
                  if type(v) != type(np.ndarray([]))}
        mydict.update({k: ', '.join([f"{vi:.4f}" for vi in v])
                       for k, v in hresults.__dict__.items()
                       if type(v) == type(np.ndarray([]))})

    return mydict, expname


def dict_to_str(mydict):
    mylist = [f"{k} \t {v}" for k, v in mydict.items()]
    return '\n'.join(mylist)


# =======THE APP=======
st.title('ODNPLab: One-Step ODNP Processing \n Powered by DNPLab')
st.markdown(f"""
## How to use
1. Collect your ODNP data on [UCSB CNSI EMXplus]({CNSI_EMX_LINK}).
2. Save your data in an experiment folder. For demo only here we use `my_odnp_exp`.
3. Your experiment folder should look like the following:
```
my_odnp_exp/
            1/...
            2/...
            3/...
            ...
            t1_powers.mat
            power.mat
```
4. Right click the experiment folder `my_odnp_exp` and create a zip file:
- For windows 7 and above you can use 'add to zip file'.
- For Mac you can use 'compress'.

5. Upload the zip file and click run.
""")

st.markdown("## Upload a Zip file")
uploaded_file = st.file_uploader("Here ->", type="zip")

if uploaded_file is not None:

    # Parameters
    ppar = ProcParameter()
    ppar.verbose = False
    ppar = set_ppar(ppar)

    hpar = HydrationParameter()
    hpar = set_hpar(hpar)

    if st.button("Run"):

        results, expname = run(uploaded_file, ppar=ppar, hpar=hpar)
        st.write(results)
        st.markdown(get_table_download_link(dict_to_str(results), filename=expname),
                    unsafe_allow_html=True)
    else:
        st.write("^ Click Me ")

st.markdown(f"""
## Demo
6. For demo, click [here]({DEMO_DATA_LINK}) to download a zip file and upload. The demo data came from (500 $\mu$M 4OH-TEMPO in water, {'$k_{sigma} = 95 s^{-1} M^{-1}$'}).

## Issues/Support
7. Report any issue [here]({ISSUE_COMPLAINT_LINK}) and I will get back to you shortly.
""")