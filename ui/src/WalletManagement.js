import React, { Component } from 'react';
import $ from 'jquery';
import DefaultWallet from './widgets/default_wallet.js';
import WalletList from './widgets/wallet_list.js';
import NewWalletForm from './widgets/new_wallet_form.js';
import axios from 'axios';

class WalletManagement extends Component {

  constructor(props) {
    super(props);
    this.state = {
      'default_wallet': null,
      'wallets': null
    }
    this.getDefaultWallet = this.getDefaultWallet.bind(this);
    this.getWallets = this.getWallets.bind(this);
  }

  componentDidMount() {
    this.getDefaultWallet();
    this.getWallets();
  }

  getDefaultWallet() {
    axios.get("/info_wallet").then((response) => {
      let data = response.data;
      if(data.hasOwnProperty('address')) {
        this.setState((state) => {
          state['default_wallet'] = data;
          return state;
        });
      }
      else {
        this.setState((state) => {
          state['default_wallet'] = null;
          return state;
        });
      }
    });
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
      <div className="container-fluid">
        <div className="row">
          <DefaultWallet wallet={this.state.default_wallet} refresh={() => {this.getWallets(); this.getDefaultWallet();}} />
        </div>
        <div className="row">
          <div className="col-lg-6 col-md-12 col-sm-12">
            <WalletList refresh={() => {this.getWallets(); this.getDefaultWallet();}} wallets={this.state.wallets} 
                        default_wallet={this.state.default_wallet} notify={this.props.notify} />
          </div>
        </div>
        <div className="row">
          <div className="col-lg-3 col-md-6 col-sm-6">
            <NewWalletForm refresh={this.getWallets} notify={this.props.notify}/>
          </div>
        </div>
      </div>
    );
  }
}

export default WalletManagement;