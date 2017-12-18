import React, { Component } from 'react';
import {MCardStats} from '../components/card.js';
import axios from "axios";

class Miner extends Component {
  constructor(props) {
    super(props);
    this.state = {
      'running': null
    }
    this.minerChangeStatus = this.minerChangeStatus.bind(this);
  }

  componentWillMount() {
    this.update();
  }

  update() {
    axios.get("/status_miner").then((response) => {
      let data = response.data;
      this.setState((state) => {
        state['running'] = data.running;
        return state;
      });
    });
  }

  minerChangeStatus() {
    if(this.state.running === null) {
      return;
    }

    if(this.state.running) {
      axios.get("/stop_miner").then((response) => {
        this.update();
      });
    }
    else {
      axios.get("/start_miner").then((response) => {
        this.update();
      });
    }
  }

  render() {
    let content = 'Loading';
    let color = 'yellow';
    let button_text = 'Loading';
    let button_type = "info";
    if(this.state.running === false) {
      content = "Closed";
      color = "red";
      button_text = "Start";
      button_type = "success";
    }
    else if(this.state.running) {
      content = "Running";
      color = "green";
      button_text = "Stop";
      button_type = "danger";
    }
    return (
      <div className="col-lg-6 col-md-12 col-sm-12">
        <div className="card card-stats">
          <div className="card-header" data-background-color={color}>
            <i className="material-icons">build</i>
          </div>
          <div className="card-content">
            <p className="category">Miner Status</p>
            <h3 className="title">{content}</h3>
          </div>
          <div className="card-footer">
            <div className="stats" style={{"float":"right"}}>
              <button className={'btn btn-' + button_type} onClick={this.minerChangeStatus}>{button_text}</button>
            </div>
          </div>
        </div>
      </div>
    );
  }
}

export default Miner;