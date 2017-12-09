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
      'txs': {
        'columns': {},
        'rows': null
      },
      'blocks': {
        'columns': {},
        'rows': null
      }
    }
    this.getDefaultWallet = this.getDefaultWallet.bind(this);
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
      else {
        this.setState((state) => {
          state['default_wallet'] = null;
          return state;
        });
      }
    });
  }

  initBlockchainStats() {
    $.get("/txs", (data) => {
      const columns = {'from': 'Sender', 'to': 'Receiver', 'amount': 'Value'};
      const rows = [];
      data.map((row, i) => {
        if(rows.length < 20) {
          let new_row = [];
          Object.keys(columns).map((col, j) => {
            new_row.push(row[col]);
          });
          rows.push(new_row);
        }
      });

      this.setState((state) => {
        state['txs'] = {
          'rows': rows,
          'columns': columns
        }
        return state;
      });
    });

    $.get("/peers", (data) => {
      const columns = {'ip': 'IP Addres', 'port': 'Port', 'rank': 'Rank', 'length': 'Blockcount'};
      const rows = [];
      data.map((row, i) => {
        if(row.rank !== 30 && rows.length < 10) {
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
      const columns = {'length': 'Height', 'time': 'Timestamp', 'txs_count': 'Transactions', 'miner': 'Mined by'};
      const rows = [];
      data.map((row, i) => {
        if(rows.length < 10) {
          let new_row = [];
          new_row.push(row.length);
          new_row.push(timestampToDatetime(row.time));
          new_row.push(row.txs.length);
          new_row.push(row.miner);
          rows.push(new_row);
        }
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
    let txs = null;
    if(this.state.default_wallet !== null ) {
      balance = <Balance balance={this.state.default_wallet.balance} name={this.state.default_wallet.name} 
                         notify={this.props.notify} refresh={() => {this.getDefaultWallet(); this.initBlockchainStats();}} />;
      address = <Address address={this.state.default_wallet.address} name={this.state.default_wallet.name} notify={this.props.notify} />;
    }
    if(this.state.txs.rows !== null && this.state.txs.rows.length > 0) {
      txs = <div className="col-lg-6 col-md-12">
              <MCardTable color="green" title="Waiting Transactions" description="List of waiting transactions in the pool"
               columns={this.state.txs.columns} rows={this.state.txs.rows}/>
            </div>;
    }
    return (
      <div className="container-fluid">
        <div className="row">
          <Blockcount />
          {address}
          {balance}
        </div>
        <div className="row">
          {txs}
          <div className="col-lg-6 col-md-12">
            <MCardTable color="blue" title="Blocks" description="Most recent blocks"
             columns={this.state.blocks.columns} rows={this.state.blocks.rows}/>
          </div>
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
