import React, { Component } from 'react';
import $ from 'jquery';
import DefaultWallet from './widgets/default_wallet.js';
import WalletList from './widgets/wallet_list.js';
import MAlert from './components/alert.js';

class WalletManagement extends Component {

  constructor(props) {
    super(props);
    this.state = {
      'default_wallet': null,
      'wallets': null
    }
  }

  componentDidMount() {
    this.getDefaultWallet();
    this.getWallets();
  }

  getDefaultWallet() {
    $.get("/info_wallet", (data) => {
      if(data.hasOwnProperty('address')) {
        this.setState((state) => {
          state['default_wallet'] = data;
          return state;
        });
      }
    });
  }

  getWallets() {
    $.get("/wallets", (data) => {
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
      <div className="container-fluid">
        <div className="row">
          <DefaultWallet wallet={this.state.default_wallet} />
        </div>
        <div className="row">
          <WalletList wallets={this.state.wallets} />
        </div>
      </div>
    );
  }
}

export default WalletManagement;