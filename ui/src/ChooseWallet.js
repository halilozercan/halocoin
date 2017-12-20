import React, { Component } from 'react';
import $ from 'jquery';
import DefaultWallet from './widgets/default_wallet.js';
import WalletList from './widgets/wallet_list.js';
import NewWalletForm from './widgets/new_wallet_form.js';
import Miner from './widgets/miner.js';
import Balance from './widgets/balance.js';
import Address from './widgets/address.js';
import axios from 'axios';
import {Tabs, Tab} from 'material-ui/Tabs';
import Paper from 'material-ui/Paper';

const bottomBarStyle = {
  position: 'absolute', 
  bottom: 0, 
  width: '100%',
  padding: 16
};

const styles = {
  headline: {
    fontSize: 24,
    paddingTop: 16,
    marginBottom: 12,
    fontWeight: 400,
  },
};

class ChooseWallet extends Component {

  constructor(props) {
    super(props);
    this.state = {
      'wallets': null
    }
    this.getWallets = this.getWallets.bind(this);
  } 

  componentDidMount() {
    this.getWallets();
  }

  getWallets() {
    axios.get("/wallets").then((response) => {
      let data = response.data;
      console.log(data);
      if(data.hasOwnProperty('wallets')) {
        this.setState((state) => {
          state['wallets'] = Object.keys(data.wallets);
          return state;
        });
      }
    });
  }

  render() {
    return (
      <div>
        <Tabs>
          <Tab label="New Wallet" >
            <NewWalletForm refresh={this.getWallets} notify={this.props.notify}/>
          </Tab>
          <Tab label="Choose a Wallet" >
            <WalletList wallets={this.state.wallets} notify={this.props.notify}/>
          </Tab>
          <Tab label="Restore Wallet">
            <div>
              <h2 style={styles.headline}>Restore Wallet</h2>
              <p>
                Here will be an upload form to restore an earlier wallet
              </p>
            </div>
          </Tab>
        </Tabs>
        <Paper style={bottomBarStyle}  zDepth={1}>
          Blockcount: 225-3569
        </Paper>
      </div>
    );
  }
}

export default ChooseWallet;