import React, { Component } from 'react';
import {MCardStats, MCardTable} from './components/card.js';
import $ from "jquery";
import Blockcount from './widgets/blockcount.js';
import {timestampToDatetime} from './tools.js';
import axios from 'axios';

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
      'job_txs': {
        'columns': {},
        'rows': null
      },
      'available_jobs': {
        'columns': {},
        'rows': null
      },
      'assigned_jobs': {
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

  componentDidMount() {
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
    this.updateTxs();
    this.updatePeers();
    this.updateBlocks();
    this.updateJobTxs();
    this.updateJobs();
  }

  updateTxs() {
    axios.get("/txs").then((response) => {
      let data = response.data;
      const columns = {'from': 'Sender', 'to': 'Receiver', 'amount': 'Value'};
      const rows = [];
      data.map((row, i) => {
        if(rows.length < 20 && row.type == 'spend') {
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
  }

  updateJobTxs() {
    axios.get("/txs").then((response) => {
      let data = response.data;
      const columns = {'type': 'Type', 'from': 'Announcer', 'to': 'Target', 'amount': 'Supply'};
      const rows = [];
      data.map((row, i) => {
        if(rows.length < 20 && row.type != 'spend') {
          let new_row = [];
          Object.keys(columns).map((col, j) => {
            new_row.push(row[col]);
          });
          rows.push(new_row);
        }
      });

      this.setState((state) => {
        state['job_txs'] = {
          'rows': rows,
          'columns': columns
        }
        return state;
      });
    });
  }

  updateJobs() {
    axios.get("/jobs").then((response) => {
      let data = response.data.available;

      console.log(data);
      let columns = {'job_id': 'Job ID', 'added_at': 'Added At'};
      let rows = [];
      Object.values(data).map((row, i) => {
        if(rows.length < 20) {
          let new_row = [];
          new_row.push(row.id);
          new_row.push(row.status_list[0].block);
          rows.push(new_row);
        }
      });

      this.setState((state) => {
        state['available_jobs'] = {
          'rows': rows,
          'columns': columns
        }
        return state;
      });

      data = response.data.assigned;
      columns = {'job_id': 'Job ID', 'assigned_at': 'Assignment Block', 'assigned_to': 'Assignee'};
      rows = [];
      Object.values(data).map((row, i) => {
        if(rows.length < 20) {
          let new_row = [];
          new_row.push(row.id);
          new_row.push(row.status_list[row.status_list.length-1].block);
          new_row.push(row.status_list[row.status_list.length-1].address);
          rows.push(new_row);
        }
      });

      this.setState((state) => {
        state['assigned_jobs'] = {
          'rows': rows,
          'columns': columns
        }
        return state;
      });
    });
  }

  updatePeers() {
    axios.get("/peers").then((response) => {
      let data = response.data;
      const columns = {'ip': 'IP Address', 'port': 'Port', 'rank': 'Rank', 'length': 'Blockcount'};
      const rows = [];
      data.map((row, i) => {
        if(row.rank < 30 && rows.length < 10) {
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
  }

  updateBlocks() {
    axios.get("/block").then((response) => {
      let data = response.data.blocks;
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

    this.blockcount.update();
  }

  render() {
    let txs = null;
    if(this.state.txs.rows !== null && this.state.txs.rows.length > 0) {
      txs = <div className="col-lg-6 col-md-12">
              <MCardTable color="green" title="Waiting Transactions" description="List of waiting transactions in the pool"
               columns={this.state.txs.columns} rows={this.state.txs.rows}/>
            </div>;
    }
    return (
      <div className="container-fluid">
        <div className="row">
          <Blockcount ref={(input)=>{this.blockcount = input;}}/>
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
          <div className="col-lg-6 col-md-12">
            <MCardTable color="yellow" title="Job Transactions" description="Transactions that are special to Coinami network"
             columns={this.state.job_txs.columns} rows={this.state.job_txs.rows}/>
          </div>
        </div>
        <div className="row">
          <div className="col-lg-6 col-md-12">
            <MCardTable color="green" title="Available Jobs" description="Jobs that are currently available for bidding"
             columns={this.state.available_jobs.columns} rows={this.state.available_jobs.rows}/>
          </div>
          <div className="col-lg-6 col-md-12">
            <MCardTable color="red" title="Assigned Jobs" description="Jobs that are assigned until some time"
             columns={this.state.assigned_jobs.columns} rows={this.state.assigned_jobs.rows}/>
          </div>
        </div>
      </div>
    );
  }
}

export default MainPage;
