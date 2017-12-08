import React, { Component } from 'react';
import MButton from './components/button.js';
import {MCardStats, MCardTable} from './components/card.js';
import $ from "jquery";

class MainPage extends Component {

  constructor(props){
    super(props);
    this.state = {
      'length': '-',
      'known_length': '-',
      'default_wallet': null,
      'peers': {
        'columns': [],
        'rows': []
      }
    }
  }

  componentWillMount() {
    this.getDefaultWallet();
    this.initBlockchainStats();
  }

  getDefaultWallet() {
    $.get("/info_wallet", (data) => {
      if(data.hasOwnProperty('address')) {
        this.setState((state) => {
          state['default_wallet'] = data;
          return state;
        }, this.initWalletStats);
      }
    });
  }

  initBlockchainStats() {
    $.get("/blockcount", (data) => {
      this.setState((state) => {
        state['length'] = data.length;
        state['known_length'] = data.known_length;
        return state;
      });
    });

    $.get("/peers", (data) => {
      const columns = [];
      const rows = [];
      data.map((row, i) => {
        rows.push(row);
        if(i==0) {
          for(var col in row) {
            columns.push(col);
          }
        }
      });
      console.log(rows);
      console.log(columns);
      this.setState((state) => {
        state['peers'] = {
          'rows': rows,
          'columns': columns
        }
        return state;
      });
    });
  }

  initWalletStats() {
    $.get("/balance", (data) => {
      this.setState((state) => {
        state['balance'] = data;
        return state;
      });
    });
  }

  render() {
    const default_wallet_exists = (this.state.default_wallet !== null);
    let stats = null;
    if(default_wallet_exists) {
      stats = <div className="col-lg-3 col-md-6 col-sm-6">
                <MCardStats color="green" header_icon="info_outline" title="Balance"
                 content={this.state.balance} 
                 footer_icon="local_offer" alt_text={'Default wallet: ' + this.state.default_wallet.name}/>
              </div>;
    }
    else {
      stats = <div className="col-lg-3 col-md-6 col-sm-6">
                <MCardStats color="red" header_icon="warning" title="Default Wallet"
                 content="Not selected!" footer_icon="local_offer" 
                 alt_text='Choose one to easily inspect and manage'/>
              </div>;
    }
    return (
      <div className="container-fluid">
        <div className="row">
          <div className="col-lg-3 col-md-6 col-sm-6">
            <MCardStats color="orange" header_icon="content_copy" title="Block Count"
             content={this.state.length + '/' + this.state.known_length} 
             footer_icon="update" alt_text="Just Updated"/>
          </div>
          {stats}
        </div>
        <div className="row">
          <div className="col-lg-6 col-md-12">
            <MCardTable color="purple" title="Peers" description="List of top ranked peers in your network"
             columns={this.state.peers.columns} rows={this.state.peers.rows}/>
          </div>
        </div>
      </div>
    );
  }
}

export default MainPage;
