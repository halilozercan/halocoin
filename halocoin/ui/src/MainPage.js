import React, { Component } from 'react';
import {MCardStats, MCardTable} from './components/card.js';
import $ from "jquery";
import Blockcount from './widgets/blockcount.js';
import Balance from './widgets/balance.js';
import Address from './widgets/address.js';
import {timestampToDatetime} from './tools.js';

class MainPage extends Component {

  constructor(props){
    super(props);
    this.state = {
      'default_wallet': null,
      'peers': {
        'columns': {},
        'rows': null
      },
      'blocks': {
        'columns': {},
        'rows': null
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
        });
      }
    });
  }

  initBlockchainStats() {
    $.get("/peers", (data) => {
      const columns = {'ip': 'IP Addres', 'port': 'Port', 'rank': 'Rank', 'length': 'Blockcount'};
      const rows = [];
      data.map((row, i) => {
        if(row.rank !== 30) {
          let new_row = [];
          Object.keys(columns).map((col, j) => {
            new_row.push(row[col]);
          });
          rows.push(new_row);
        }
      });

      this.setState((state) => {
        state['peers'] = {
          'rows': rows,
          'columns': columns
        }
        return state;
      });
    });

    $.get("/block", (data) => {
      data = data.blocks;
      const columns = {'length': 'Height', 'time': 'Timestamp', 'txs_count': 'Transaction Count', 'miner': 'Mined by'};
      const rows = [];
      data.map((row, i) => {
        let new_row = [];
        new_row.push(row.length);
        new_row.push(timestampToDatetime(row.time));
        new_row.push(row.txs.length);
        new_row.push(row.miner);
        rows.push(new_row);
      });

      this.setState((state) => {
        state['blocks'] = {
          'rows': rows,
          'columns': columns
        }
        return state;
      });
    });
  }

  render() {
    let balance = null;
    let address = null;
    if(this.state.default_wallet !== null ) {
      balance = <Balance balance={this.state.default_wallet.balance} name={this.state.default_wallet.name} />;
      address = <Address address={this.state.default_wallet.address} name={this.state.default_wallet.name} />;
    }
    return (
      <div className="container-fluid">
        <div className="row">
          <Blockcount />
          {balance}
          {address}
        </div>
        <div className="row">
          <div className="col-lg-6 col-md-12">
            <MCardTable color="purple" title="Peers" description="List of top ranked peers in your network"
             columns={this.state.peers.columns} rows={this.state.peers.rows}/>
          </div>
          <div className="col-lg-6 col-md-12">
            <MCardTable color="blue" title="Blocks" description="Most recent blocks"
             columns={this.state.blocks.columns} rows={this.state.blocks.rows}/>
          </div>
        </div>
      </div>
    );
  }
}

export default MainPage;
